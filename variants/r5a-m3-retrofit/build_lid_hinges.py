"""V5 M3 eyelid hinge with a captured nut in the fixed support.

The screw seats against the fixed prong, so the moving leaf is free.
The stock 0.5 mm gap and lid axis are preserved.
"""

import argparse
import itertools
import json
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, export_part, open_bore
from check_structural import Scene
from servo_clamps import box, overlaps


def nut(x, y, z, side, across_flats, length):
    plane = cq.Plane(origin=(x, y, z), xDir=(0, 1, 0), normal=(-side, 0, 0))
    return cq.Workplane(plane).polygon(6, across_flats, circumscribed=True).extrude(length).val()


def hinge_clearances(eye_x, side):
    y, z = -36.25, 112.5
    outer_face = eye_x + side * 25.8
    face = outer_face - side * 1.8
    inward = (-side, 0, 0)
    return (
        cylinder(2.95, (outer_face + side * 0.1, y, z), inward, 1.9),
        nut(face - side * 1.3, y, z, side, 5.8, 2.65),
        box(face - side * 2.625, y + 3.0, z, 2.65, 6.0, 5.9),
    )


def hinge(deck, eye_x, side):
    y, z = -36.25, 112.5
    outer_face = eye_x + side * 25.8
    face = outer_face - side * 1.8
    inward = (-side, 0, 0)
    # Add a fixed landing outside the old prong; the inner bearing face
    # remains at +/-19.8 from the eye center.
    pad = cylinder(4.65, (eye_x + side * 22.65, y, z), (side, 0, 0), 3.15)
    new = deck.fuse(pad).clean()
    new = new.cut(*hinge_clearances(eye_x, side)).clean()
    new = open_bore(new, (eye_x + side * 23, y, z), inward, 10)
    # Recessing the head leaves 1.3 mm of the 1.5 mm lid leaf on the pin.
    screw = cylinder(1.5, (face, y, z), inward, 6)
    screw = screw.fuse(cylinder(2.75, (face, y, z), (side, 0, 0), 3))
    installed_nut = nut(face - side * 1.3, y, z, side, 5.5, 2.4)
    return new, screw, installed_nut


def build(baseline, output, mounts):
    scene = Scene(baseline)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    original = {item["name"]: item["shape"] for item in scene.items}
    deck = original["P36"]
    carrier = original["P45"]
    if mounts:
        path = next((mounts / "STEP").glob("P45_*_M3.step"))
        carrier = cq.importers.importStep(str(path)).val()
    # The heads of the outer hinge screws share the pitch axis. Remove
    # 0.6 mm from the inside face of each pitch-carrier arm at the axis.
    for side in (-1, 1):
        recess = cylinder(3.05, (side * 59.8, -36.25, 112.5), (side, 0, 0), 1.3)
        carrier = carrier.cut(recess).clean()
    lids = {}
    hardware = []
    for tag, eye_x, pid in (("L", -33.75, "P39"), ("R", 33.75, "P40")):
        lid = original[f"{pid}_{tag}"]
        for side in (-1, 1):
            deck, screw, nut_shape = hinge(deck, eye_x, side)
            lid = open_bore(lid, (eye_x + side * 18.55, -36.25, 112.5), (1, 0, 0), 5)
            key = f"{tag}_{side}"
            hardware.extend(((f"lid_pin_{key}_screw", screw), (f"lid_pin_{key}_nut", nut_shape)))
        lids[f"{pid}_{tag}"] = lid
    for item in scene.items:
        if item["name"] in lids:
            item["shape"] = lids[item["name"]]
        if item["name"] == "P36":
            item["shape"] = deck
        if item["name"] == "P45":
            item["shape"] = carrier
    added = deck.cut(original["P36"])
    items_to_check = hardware + [("lid_hinge_new_material", added)]

    cases = [dict(yaw=0, pitch=0, lid_L=0, lid_R=0)]
    for yaw, pitch, left, right in itertools.product((-20, 20), (-12, 12), (0, 25, 50), (0, 50)):
        cases.append(dict(yaw=yaw, pitch=pitch, lid_L=left, lid_R=right))
    findings = []
    for index, pose in enumerate(cases):
        posed, _ = scene.pose(**pose)
        for key, shape in items_to_check:
            others = [(i["name"], i["shape"]) for i in posed
                      if not (key == "lid_hinge_new_material" and i["name"] == "P36")
                      and (index == 0 or i["group"] != "fixed")]
            for name, volume in overlaps(shape, others):
                findings.append(dict(pose=pose, a=key, b=name, overlap_mm3=round(volume, 4)))
        if index % 8 == 0:
            print(f"Pose {index + 1}/{len(cases)}: {len(findings)} overlaps", flush=True)

    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_LID_HINGE_CLEARANCE" if not findings else "FAIL_LID_HINGE_CLEARANCE",
                  physical_tested=False, poses=len(cases), findings=findings,
                  scope="Four hinge screws and captive nuts; stop and horn linkages checked separately.")
    (output / "lid_hinge_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1
    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    for pid, shape in [("P36", deck), ("P45", carrier)] + [(k.split("_")[0], v) for k, v in lids.items()]:
        assert shape.isValid() and len(shape.Solids()) == 1, pid
        export_part(parts[pid], shape, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mounts", type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.output, args.mounts))
