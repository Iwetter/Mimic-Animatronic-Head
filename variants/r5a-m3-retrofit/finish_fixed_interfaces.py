"""Provide tool access and nut seats for the V5 fixed M3 interfaces."""

import argparse
import json
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, export_part
from check_fixed_hardware import seats
from check_structural import Scene
from servo_clamps import box


def captured(shape, point, axis, loading):
    """Cut an M3 nut pocket and an open slide-in slot on its service side."""
    z = cq.Vector(*axis)
    y = cq.Vector(*loading)
    x = y.cross(z)
    p = cq.Vector(*point)
    plane = cq.Plane(p, x, z)
    hexagon = cq.Workplane(plane).polygon(6, 6.45, circumscribed=True).extrude(2.65).val()
    slot = cq.Workplane(plane).box(6.5, 9.2, 2.65).val().translate(y * 4.6 + z * 1.325)
    return shape.cut(hexagon.fuse(slot)).clean()


def bore(shape, point, axis, length, radius=1.7):
    return shape.cut(cylinder(radius, point, axis, length)).clean()


def build(baseline, stages, output):
    scene = Scene(baseline)
    original = {item["name"]: item["shape"] for item in scene.items}
    meta = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    solids = dict(original)
    for directory, ids in (
        ("structural", ("P21", "P22", "P25", "P26", "P27", "P28", "P30", "P31", "P32")),
        ("mounts", ("P41",)),
        ("jaw_drive", ("P33",)),
        ("horn_adapters_new", ("P36",)),
    ):
        for pid in ids:
            step = next((stages / directory / "STEP").glob(pid + "*_M3.step"))
            solids[pid] = cq.importers.importStep(str(step)).val()
    changed = set()

    def update(pid, solid):
        if not solid.isValid() or len(solid.Solids()) != 1:
            raise ValueError((pid, "invalid hardware seat"))
        solids[pid] = solid
        changed.add(pid)

    for sx, upper, cheek in ((-1, "P23", "P30"), (1, "P24", "P31")):
        # Top face mask mounts have no straight nut access from behind
        # the side wall. Load each nut from the inner side of the wall.
        face = captured(solids[upper], (sx * 74.5, -49.5, 125.5), (0, 1, 0), (-sx, 0, 0))
        update(upper, bore(face, (sx * 74.5, -51, 125.5), (0, 1, 0), 10))
        cheek_solid = captured(solids[cheek], (sx * 59, -47.5, 90), (0, 1, 0), (0, 0, -1))
        cheek_solid = bore(cheek_solid, (sx * 59, -49, 90), (0, 1, 0), 8)
        update(cheek, bore(cheek_solid, (sx * 65, -15, 88.5), (0, 0, 1), 8, 4.1))

        # Back up the thin upper jaw strut around its new side-loaded
        # nut slot. The slot opens downward for installation.
        block = box(sx * 61.0, -16, 64.5, 10, 8.4, 10)
        jaw = solids["P32"].fuse(block).clean()
        jaw = captured(jaw, (sx * 62, -16, 60), (-sx, 0, 0), (0, 0, -1))
        jaw = bore(jaw, (sx * 66.1, -16, 60), (-sx, 0, 0), 12.5)
        jaw = bore(jaw, (sx * 65, -15, 70.1), (0, 0, -1), 3.25, 4.25)
        update("P32", bore(jaw, (sx * 65, -15, 67), (0, 0, -1), 3.25))

        # Make the eye-deck side nut and the arch nuts reachable.
        update("P36", bore(solids["P36"], (sx * 62, -12, 76), (-sx, 0, 0), 7, 4.15))
        deck = bore(solids["P41"], (sx * 65, 2, 151.5), (-sx, 0, 0), 6, 4.1)
        for y in (-15, 15):
            deck = captured(deck, (sx * 66, y, 153), (-sx, 0, 0), (0, 0, -1))
            deck = bore(deck, (sx * 67, y, 153), (-sx, 0, 0), 8.5)
        update("P41", deck)

        # The lower tooth carrier's old small bore stopped just short
        # of the underside. Continue the M3 bore past the new screw tip.
        update("P33", bore(solids["P33"], (sx * 32, -41, 37), (0, 0, -1), 18))
    for pid, y, underside in (("P25", -45, 188), ("P28", -45, 188), ("P28", 52, 204.5)):
        update(pid, bore(solids[pid], (0, y, underside), (0, 0, -1), 7, 4.1))

    # Spot-face the two sides that use stock 7 mm flat washers wherever
    # the original narrower hardware left a small lip in the seat.
    contract = json.loads((baseline / "bom/parts.json").read_text())
    reliefs = {
        "H_BASE_P21": ("P21", "head_washer"), "H_BASE_P22": ("P22", "head_washer"),
        "H_ARCH_P25": ("P25", "nut_washer"), "H_ARCH_P26": ("P26", "nut_washer"),
        "H_ARCH_P27": ("P27", "nut_washer"), "H_CREST": ("P28", "head_washer"),
        "H_MAX_FACE": ("P32", "head_washer"), "H_JAW_CRADLE_BASE": ("P44", "head_washer"),
    }
    path = next((stages / "jaw_drive/STEP").glob("P44*_M3.step"))
    solids["P44"] = cq.importers.importStep(str(path)).val()
    for joint in contract["hardware"]:
        joint_id = joint["id"]
        if joint_id.startswith("H_ZYG_ROOT_"):
            pid = "P21" if joint_id.endswith("-1") else "P22"
            directions = ("head_washer", "nut_washer")
        elif joint_id in reliefs:
            pid, washer = reliefs[joint_id]
            directions = (washer,)
        else:
            continue
        solid = solids[pid]
        for location in joint["location_mm"]:
            face, axis, grip = seats(joint_id, location, joint["nominal_grip_mm"])
            for washer in directions:
                depth = -0.7 if washer == "head_washer" else grip - 0.03
                start = tuple(v + d * depth for v, d in zip(face, axis))
                solid = bore(solid, start, axis, 0.74, 3.65)
        update(pid, solid)

    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(parents=True, exist_ok=True)
    for pid in sorted(changed):
        path = export_part(meta[pid], solids[pid], output)
        print(pid, path, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "stages", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    build(args.baseline, args.stages, args.output)
