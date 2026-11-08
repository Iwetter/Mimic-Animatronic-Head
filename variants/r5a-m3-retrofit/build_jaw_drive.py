"""Clamp the original V5 double-ended jaw horn with two M3 screws."""

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, export_part, open_bore
from check_structural import Scene
from servo_clamps import box, overlaps


Y, Z = 12.5, 56.25


def hex_x(x, y, z, diameter, length):
    plane = cq.Plane(origin=(x, y, z), xDir=(0, 1, 0), normal=(1, 0, 0))
    return cq.Workplane(plane).polygon(6, diameter, circumscribed=True).extrude(length).val()


def build(baseline, structural, mounts, output):
    scene = Scene(baseline)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    original = {i["name"]: i["shape"] for i in scene.items}
    jaw = cq.importers.importStep(str(next((structural / "STEP").glob("P33*_M3.step")))).val()
    cradle = cq.importers.importStep(str(next((mounts / "STEP").glob("P44*_M3.step")))).val()
    plate = cylinder(11, (-57.5, Y, Z), (1, 0, 0), 2.4).cut(
        cylinder(4.75, (-58, Y, Z), (1, 0, 0), 4))
    hardware = []
    for side in (-1, 1):
        y, z = Y + side * 6, Z + side * 5.7
        jaw = jaw.fuse(cylinder(4.1, (-64.5, y, z), (1, 0, 0), 5)).clean()
        pocket = hex_x(-63.3, y, z, 5.8, 2.65)
        slot = box(-61.975, y, z + side * 3, 2.65, 6.5, 6)
        jaw = jaw.cut(pocket.fuse(slot)).clean()
        jaw = open_bore(jaw, (-61, y, z), (1, 0, 0), 10)
        plate = open_bore(plate, (-56, y, z), (1, 0, 0), 6)
        screw = cylinder(1.5, (-55.1, y, z), (-1, 0, 0), 8).fuse(
            cylinder(2.75, (-55.1, y, z), (1, 0, 0), 3))
        for degrees in range(15):
            angle = math.radians(degrees)
            cy = Y + (y - Y) * math.cos(angle) - (z - Z) * math.sin(angle)
            cz = Z + (y - Y) * math.sin(angle) + (z - Z) * math.cos(angle)
            cradle = cradle.cut(cylinder(3.15, (-55.4, cy, cz), (1, 0, 0), 3.6)).clean()
        hardware.extend(((f"jaw_clamp_{side}_screw", screw),
                         (f"jaw_clamp_{side}_nut", hex_x(-63.1, y, z, 5.5, 2.4))))
    # Two short locating cheeks prevent the nominal 4 mm horn from sliding
    # sideways. The original spline center screw stays accessible.
    for z in (Z - 3.1, Z + 3.1):
        for y in (Y - 7, Y + 7):
            plate = plate.fuse(box(-57.65, y, z, 0.35, 3, 0.8)).clean()
    assert all(s.isValid() and len(s.Solids()) == 1 for s in (jaw, plate, cradle))

    edits = {"P33": jaw, "P44": cradle}
    for item in scene.items:
        if item["name"] in edits:
            item["shape"] = edits[item["name"]]
    new_items = hardware + [("jaw_horn_plate", plate), ("P33_new_material", jaw.cut(original["P33"]))]
    scene.items.extend(dict(name=k, shape=s, group="jaw") for k, s in new_items)
    findings = []
    for angle in range(0, 15, 2):
        items, _ = scene.pose(jaw=angle)
        for key, _ in new_items:
            item = next(i for i in items if i["name"] == key)
            others = []
            for other in items:
                name = other["name"]
                if name == key or name == "P33_new_material":
                    continue
                if name == "P33" and key == "P33_new_material":
                    continue
                if key.rsplit("_", 1)[0] == name.rsplit("_", 1)[0] and {
                    key.rsplit("_", 1)[1], name.rsplit("_", 1)[1]
                } == {"screw", "nut"}:
                    continue
                if angle and other["group"] == "jaw":
                    continue
                others.append((name, other["shape"]))
            for name, volume in overlaps(item["shape"], others):
                findings.append(dict(jaw=angle, a=key, b=name, overlap_mm3=round(volume, 4)))
        print(f"Jaw {angle} degrees: {len(findings)} overlaps", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_JAW_HORN_CLEARANCE" if not findings else "FAIL_JAW_HORN_CLEARANCE",
                  poses=8, physical_tested=False, findings=findings,
                  scope="Horn clamp, nominal servo, and revised mandible. Pivot and stop hardware checked separately.")
    (output / "jaw_horn_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1
    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    export_part(parts["P33"], jaw, output)
    export_part(parts["P44"], cradle, output)
    export_part(dict(id="A30", name="jaw_horn_plate", qty=1, print_rotation_xyz_deg=[0, 90, 0]),
                plate, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "structural", "mounts", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.structural, args.mounts, args.output))
