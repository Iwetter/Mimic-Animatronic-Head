"""Use M3 socket screws to grip the original smooth V5 yaw shafts."""

import argparse
import itertools
import json
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, export_part, open_bore
from check_structural import Scene
from servo_clamps import box, overlaps


EX = 33.75
EY = -36.25


def hex_prism(point, axis, width, length):
    plane = cq.Plane(origin=point, xDir=(0, 0, 1), normal=axis)
    return cq.Workplane(plane).polygon(6, width, circumscribed=True).extrude(length).val()


def shaft_clamp(shape, x, y, z, orientation):
    """Build a slide-in nut pocket with a shoulder behind the nut."""
    if orientation == "back":
        pad = box(x, y + 3.25, z, 8.5, 8.1, 7.8)
        nut_base, axis = (x, y + 2.8, z), (0, 1, 0)
        slot = box(x, y + 4.125, z + 2.5, 6.6, 2.65, 5.0)
        seat = (x, y + 7.3, z)
        wall, shank_axis = (x, y + 3.3, z), (0, -1, 0)
    else:
        pad = box(x - 3.25, y, z, 8.1, 8.5, 7.6)
        nut_base, axis = (x - 2.8, y, z), (-1, 0, 0)
        slot = box(x - 4.125, y, z - 2.5, 2.65, 6.6, 5.0)
        seat = (x - 7.3, y, z)
        wall, shank_axis = (x - 3.3, y, z), (1, 0, 0)

    result = shape.fuse(pad).clean()
    result = result.cut(hex_prism(nut_base, axis, 5.8, 2.65).fuse(slot)).clean()
    result = open_bore(result, wall, shank_axis, 10)
    # Reopen the original smooth bearing axis after adding the clamp body.
    result = result.cut(cylinder(1.6, (x, y, z - 10), (0, 0, 1), 20)).clean()
    shank = cylinder(1.5, seat, shank_axis, 6)
    head = cylinder(2.75, seat, axis, 3)
    screw = shank.fuse(head)
    installed_nut = hex_prism(nut_base, axis, 5.5, 2.4)
    return result, screw, installed_nut


def build(baseline, output):
    scene = Scene(baseline)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    original = {item["name"]: item["shape"] for item in scene.items}
    globe, globe_screw, globe_nut = shaft_clamp(original["P34_L"], -EX, EY, 112.5, "back")
    crank, crank_screw, crank_nut = shaft_clamp(original["P37_L"], -EX, EY, 88.6, "side")
    spacer = cylinder(3.5, (-EX, EY, 105.2), (0, 0, 1), 3).cut(
        cylinder(1.7, (-EX, EY, 104.9), (0, 0, 1), 3.6)).clean()
    assert all(s.isValid() and len(s.Solids()) == 1 for s in (globe, crank, spacer))
    # The crank now provides the bottom shoulder. A printed shim preserves
    # the old upper collar stack height, without adding a radial screw.
    scene.items = [i for i in scene.items if not i["name"].startswith("COLLAR_")]
    edits = {}
    added_names = set()
    for tag, dx in (("L", 0), ("R", 2 * EX)):
        for pid, shape, screw, installed_nut, group in (
            ("P34", globe, globe_screw, globe_nut, "eye"),
            ("P37", crank, crank_screw, crank_nut, "crank"),
        ):
            key = f"{pid}_{tag}"
            edits[key] = shape.translate((dx, 0, 0))
            for label, solid in (("screw", screw), ("nut", installed_nut)):
                name = f"{key}_{label}"
                scene.items.append(dict(name=name, shape=solid.translate((dx, 0, 0)), group=f"{group}_{tag}"))
                added_names.add(name)
        name = f"A20_{tag}"
        scene.items.append(dict(name=name, shape=spacer.translate((dx, 0, 0)), group=f"eye_{tag}"))
        added_names.add(name)
    for item in scene.items:
        key = item["name"]
        if key in edits:
            item["shape"] = edits[key]
            scene.items.append(dict(name=f"{key}_new_material", shape=edits[key].cut(original[key]),
                                    group=item["group"]))
            added_names.add(f"{key}_new_material")

    cases = [dict(yaw=0, pitch=0, lid_L=0, lid_R=0)]
    cases.extend(dict(yaw=y, pitch=p, lid_L=lid, lid_R=lid)
                 for y, p, lid in itertools.product((-20, 20), (-12, 12), (0, 50)))
    findings = []
    for index, pose in enumerate(cases):
        items, _ = scene.pose(**pose)
        for item in items:
            key = item["name"]
            if key not in added_names:
                continue
            others = []
            for other in items:
                name = other["name"]
                if name == key or name.endswith("_new_material"):
                    continue
                if key.endswith("_new_material") and name == key.removesuffix("_new_material"):
                    continue
                if key.endswith("_screw") and (name == key.removesuffix("_screw") + "_nut"
                                               or name == "STEEL_yaw_shaft_" + key.split("_")[1]):
                    continue
                if key.endswith("_nut") and name == key.removesuffix("_nut") + "_screw":
                    continue
                if index and other["group"] == item["group"]:
                    continue
                others.append((name, other["shape"]))
            for name, volume in overlaps(item["shape"], others):
                findings.append(dict(pose=pose, a=key, b=name, overlap_mm3=round(volume, 4)))
        print(f"Pose {index + 1}/{len(cases)}: {len(findings)} overlaps", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_YAW_CLAMP_CLEARANCE" if not findings else "FAIL_YAW_CLAMP_CLEARANCE",
                  physical_tested=False, poses=len(cases), findings=findings,
                  scope="Globe and crank shaft clamps only. Intended screw contact with the smooth shaft and threaded nut excluded.")
    (output / "yaw_clamp_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1
    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    export_part(parts["P34"], globe, output)
    export_part(parts["P37"], crank, output)
    export_part(dict(id="A20", name="yaw_axial_shim", qty=2, print_rotation_xyz_deg=[0, 0, 0]),
                spacer, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.output))
