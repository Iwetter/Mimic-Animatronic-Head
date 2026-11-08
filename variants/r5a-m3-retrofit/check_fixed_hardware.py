"""Inspect nominal fixed-joint screw and nut envelopes in the V5 CAD."""

import argparse
import json
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, fixed_hardware
from check_structural import Scene
from servo_clamps import overlaps


def seats(joint, location, nominal_grip):
    x, y, z = location
    side = 1 if x > 0 else -1
    if joint.startswith("H_BASE_") or joint == "H_JAW_CRADLE_BASE":
        return (x, y, 10), (0, 0, -1), 10
    if joint == "H_NECK_FLANGE":
        return (x, y, 6), (0, 0, -1), 12
    if joint == "H_CREST":
        top, bottom = {-45: (200, 188), 2: (226.3, 215.0), 52: (216.3, 204.5)}[y]
        return (x, y, top), (0, 0, -1), top - bottom
    if joint == "H_TEETH_P42":
        return (x, y, 56), (0, 0, 1), 8
    if joint == "H_TEETH_P43":
        return (x, y, 36), (0, 0, -1), 9.8
    if joint.startswith("H_ZYG_ROOT"):
        return (x, y, 88.5), (0, 0, -1), 18.5
    if joint.startswith("H_ZYG_P"):
        return location, (0, 1, 0), 14.5
    if joint.startswith(("H_FACE_", "H_ZYG_P")) or joint == "H_MAX_FACE":
        return location, (0, 1, 0), nominal_grip
    return location, (-side, 0, 0), nominal_grip


def hardware_shapes(face, direction, grip, length, rear_washer=0.5):
    origin = cq.Vector(*face)
    axis = cq.Vector(*direction)
    under_head = origin - axis * 0.5
    shank = cylinder(1.5, tuple(under_head), direction, length)
    head = cylinder(2.75, tuple(under_head), tuple(-axis), 3)
    nut_plane = cq.Plane(origin=origin + axis * (grip + rear_washer),
                         xDir=(0, 0, 1) if direction[0] or direction[1] else (1, 0, 0),
                         normal=axis)
    nut = cq.Workplane(nut_plane).polygon(6, 5.5, circumscribed=True).extrude(2.4).val()
    washer = cylinder(3.5, tuple(under_head), direction, 0.5).cut(
        cylinder(1.6, tuple(under_head), direction, 0.5))
    parts = {"shank": shank, "head": head, "nut": nut, "head_washer": washer}
    if rear_washer:
        start = tuple(origin + axis * grip)
        parts["nut_washer"] = cylinder(3.5, start, direction, rear_washer).cut(
            cylinder(1.6, start, direction, rear_washer))
    return parts


def audit(baseline, structural, output, final):
    scene = Scene(baseline)
    shapes = {i["name"]: i["shape"] for i in scene.items}
    for stage in (structural, final):
        if stage:
            for path in (stage / "STEP").glob("P*_M3.step"):
                pid = path.name.split("_")[0]
                if pid in shapes:
                    shapes[pid] = cq.importers.importStep(str(path)).val()
    contract = json.loads((baseline / "bom/parts.json").read_text())
    old_hardware = {h["id"]: h for h in contract["hardware"]}
    findings, modeled = [], []
    for row in fixed_hardware(contract):
        joint = row["joint"]
        if joint == "H_NECK_LOCK":
            continue  # checked by check_structural.py
        baseline_row = old_hardware[joint]
        length = int(row["screws"].split("x")[1])
        for number, location in enumerate(baseline_row["location_mm"], 1):
            face, direction, grip = seats(joint, location, baseline_row["nominal_grip_mm"])
            rear_washer = 0.5 if row["washers"] == 2 * row["quantity"] else 0
            extra = length - grip - 0.5 - rear_washer - 2.4
            if extra < 0.5:
                findings.append(dict(joint=joint, position=number, issue="short engagement",
                                     beyond_nut_mm=round(extra, 3)))
            for label, shape in hardware_shapes(face, direction, grip, length, rear_washer).items():
                for name, volume in overlaps(shape, shapes.items()):
                    findings.append(dict(joint=joint, position=number, issue=label, part=name,
                                         overlap_mm3=round(volume, 4)))
            modeled.append(dict(joint=joint, position=number, seat=face, axis=direction,
                                grip_mm=grip, screw=row["screws"], beyond_nut_mm=round(extra, 3)))
        print(joint, len(findings), flush=True)
    report = dict(status="PASS_FIXED_HARDWARE_CAD" if not findings else "FAIL_FIXED_HARDWARE_CAD",
                  scope="Neutral nominal head, shank and nut envelopes. 0.5 mm nominal washer thickness.",
                  physical_tested=False, joints=modeled, findings=findings)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return bool(findings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "structural", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--final", type=Path)
    args = parser.parse_args()
    raise SystemExit(audit(args.baseline, args.structural, args.output, args.final))
