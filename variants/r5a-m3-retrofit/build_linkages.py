"""Fit the V5 pushrods and yaw ties to the M3 horn adapter shoulders."""

import argparse
import itertools
import json
import math
from pathlib import Path

import cadquery as cq

from build_horn_adapters import adapter, capsule, horn_frame, locations, pad
from build_structural import cylinder, export_part, open_bore
from check_structural import Scene
from servo_clamps import box, overlaps


EX, EY = 33.75, -36.25


def from_step(folder, pid):
    return cq.importers.importStep(str(next((folder / "STEP").glob(pid + "*_M3.step")))).val()


def axial_fastener(point, direction, length, end_face):
    """Return a nominal cap screw and two full-height jam nuts."""
    axis = cq.Vector(*direction)
    origin = cq.Vector(*point)
    screw = cylinder(1.5, point, direction, length).fuse(cylinder(2.75, point, tuple(-axis), 3))
    x_dir = (0, 0, 1) if direction[0] else (1, 0, 0)
    nuts = []
    for depth in (0, 2.4):
        plane = cq.Plane(origin=cq.Vector(*end_face) + axis * depth, xDir=x_dir, normal=axis)
        nuts.append(cq.Workplane(plane).polygon(6, 5.5, circumscribed=True).extrude(2.4).val())
    return screw, nuts[0].fuse(nuts[1])


def sleeve(point, direction, length):
    start = cq.Vector(*point) - cq.Vector(*direction) * 0.05
    return cylinder(3.15, point, direction, length).cut(
        cylinder(1.7, tuple(start), direction, length + 0.1)).clean()


def arc_clearance(center, r, rad, start_deg, end_deg, bottom, height):
    cx, cy = center
    steps = math.ceil((end_deg - start_deg) / 0.5)
    angles = [math.radians(start_deg + (end_deg - start_deg) * i / steps) for i in range(steps + 1)]
    xy = [(cx - (r + rad) * math.sin(a), cy + (r + rad) * math.cos(a)) for a in angles]
    xy += [(cx - (r - rad) * math.sin(a), cy + (r - rad) * math.cos(a)) for a in reversed(angles)]
    shape = cq.Workplane("XY", origin=(0, 0, bottom)).polyline(xy).close().extrude(height).val()
    for a in (angles[0], angles[-1]):
        shape = shape.fuse(pad(cx - r * math.sin(a), cy + r * math.cos(a), bottom, rad, height))
    return shape.clean()


def flat_rod(x, start, end):
    # Draw in XY for a robust rounded end, then place in the YZ rod plane.
    plane = cq.Location(cq.Plane(origin=(x - 1.25, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0)))
    part = capsule(start, end, 3.85, 0, 2.5).moved(plane)
    for (y, z), diameter in zip((start, end), (3.4, 4.95)):
        part = part.cut(cylinder(diameter / 2, (x - 2, y, z), (1, 0, 0), 4)).clean()
    return part


def dogleg_lid_rod():
    y = -26.45
    lower_x, upper_x = 56.9, 61.3
    lower = flat_rod(lower_x, (y, 108.4), (y, 145))
    upper = flat_rod(upper_x, (y, 165), (y, 186))
    # Fill the two intermediate ends; the only pivots are at 108.4 and 186.
    def fill(x, z):
        return cylinder(3.85, (x - 1.25, y, z), (1, 0, 0), 2.5)
    start, end = cq.Vector(lower_x, y, 144), cq.Vector(upper_x, y, 166)
    spine = end - start
    normal = spine.normalized()
    local_x = cq.Vector(0, 1, 0).cross(normal)
    plane = cq.Plane(origin=(start + end) / 2, xDir=local_x, normal=normal)
    ramp = cq.Workplane(plane).box(2.5, 7.7, spine.Length).val()
    rod = lower.fuse(upper, ramp, fill(lower_x, 145), fill(upper_x, 165)).clean()
    # The lower pin has a 4.7 mm fixed shoulder and a recessed cap head.
    return rod.cut(cylinder(2.475, (55, y, 108.4), (1, 0, 0), 5),
                   cylinder(2.98, (57.31, y, 108.4), (1, 0, 0), 2)).clean()


def lid_lower_pin(lid, sign):
    y, z = -26.45, 108.4
    body = cylinder(4.05, (sign * 49.25, y, z), (sign, 0, 0), 3.9)
    shoulder = cylinder(2.35, (sign * 53.05, y, z), (sign, 0, 0), 4.3)
    lid = lid.fuse(body, shoulder).clean()
    direction = (sign, 0, 0)
    plane = cq.Plane(origin=(sign * 49.8, y, z), xDir=(0, 0, 1), normal=direction)
    pocket = cq.Workplane(plane).polygon(6, 5.8, circumscribed=True).extrude(2.65).val()
    access = box(sign * 51.125, y + 2.7, z, 2.65, 5.4, 6.55)
    lid = lid.cut(pocket.fuse(access)).clean()
    lid = open_bore(lid, (sign * 53.2, y, z), direction, 10)
    screw = cylinder(1.5, (sign * 57.35, y, z), (-sign, 0, 0), 8).fuse(
        cylinder(2.75, (sign * 57.35, y, z), direction, 3))
    placed_nut = cq.Workplane(plane).polygon(6, 5.5, circumscribed=True).extrude(2.4).val()
    return lid, screw, placed_nut


def lid_limit_blocks(deck, lid, sign):
    """Keep the lid limit outside the new lower rod shoulder and screw."""
    pivot_y, pivot_z = -36.25, 112.5
    # Put the stop in front of the hinge. The original rear sector
    # interferes with the enlarged lower rod shoulder.
    anchor = (pivot_y - 5.0, pivot_z)
    phase = math.pi
    radius = 9.0
    tip_y = pivot_y + radius * math.cos(phase)
    tip_z = pivot_z + radius * math.sin(phase)
    # Remove the rear sector that was sized for the old M2 stop pin.
    deck = deck.cut(box(sign * 55.05, pivot_y + 8.6, pivot_z + 2.9, 3.2, 8.8, 18.4)).clean()
    lug_loc = cq.Location(cq.Plane(origin=(52.5, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0)))
    lug = capsule(anchor, (tip_y, tip_z), 1.4, 0, 2.9).moved(lug_loc)
    if sign < 0:
        lug = lug.mirror("YZ")
    lid = lid.fuse(lug).clean()
    # The fixed pads have a short round tip. Their nominal contact lies
    # just outside the 0 to 50 degree commanded range.
    allowance = 2 * math.asin((1.4 + 1.7) / (2 * radius))
    for angle, direction in ((-3, -1), (53, 1)):
        theta = phase + math.radians(angle) + direction * allowance
        y = pivot_y + radius * math.cos(theta)
        z = pivot_z + radius * math.sin(theta)
        pin = cylinder(1.7, (sign * 53.55, y, z), (sign, 0, 0), 3.0)
        arm = box(sign * 55.05, (y + pivot_y) / 2, z, 3.0, pivot_y - y, 2.8)
        deck = deck.fuse(pin, arm).clean()
    assert all(s.isValid() and len(s.Solids()) == 1 for s in (deck, lid))
    return deck, lid


def pitch_limit_blocks(deck):
    """Catch the existing pitch-carrier tab at either end of its travel."""
    radius = 14.0
    # The moving tab is 7 mm tall. Place each 2 mm stop just outside its
    # corner at the nominal 14 degree pitch limit.
    theta = math.radians(14) + math.asin(3.5 / radius) + math.asin(2 / radius)
    y = EY + radius * math.cos(theta)
    z_delta = radius * math.sin(theta)
    for side in (-1, 1):
        z = 112.5 + side * z_delta
        limit = cylinder(2, (-65.0, y, z), (1, 0, 0), 2.5)
        bridge = box(-64.5, y, 112.5 + side * (z_delta - 1.8), 1.0, 4.0, 4.8)
        deck = deck.fuse(limit, bridge).clean()
    assert deck.isValid() and len(deck.Solids()) == 1
    return deck


def build(baseline, stages, output):
    scene = Scene(baseline)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    items = {i["name"]: i for i in scene.items}
    # Compose the newest edit of every part. Two-copy parts retain their
    # original assembly coordinate transforms.
    for name, folder, pid, dx in (
        ("P03", "structural", "P03", 0), ("P21", "structural", "P21", 0),
        ("P22", "structural", "P22", 0), ("P25", "structural", "P25", 0),
        ("P26", "structural", "P26", 0), ("P27", "structural", "P27", 0),
        ("P28", "structural", "P28", 0), ("P29", "structural", "P29", 0),
        ("P30", "structural", "P30", 0), ("P31", "structural", "P31", 0),
        ("P32", "structural", "P32", 0), ("P33", "jaw_drive", "P33", 0),
        ("P34_L", "yaw_clamps", "P34", 0), ("P34_R", "yaw_clamps", "P34", 67.5),
        ("P36", "horn_adapters_new", "P36", 0),
        ("P37_L", "yaw_clamps", "P37", 0), ("P37_R", "yaw_clamps", "P37", 67.5),
        ("P39_L", "lid_hinges", "P39", 0), ("P40_R", "lid_hinges", "P40", 0),
        ("P41", "mounts", "P41", 0), ("P44", "jaw_drive", "P44", 0),
        ("P42", "structural", "P42", 0), ("P43", "structural", "P43", 0),
        ("P45", "horn_adapters_new", "P45", 0),
    ):
        items[name]["shape"] = from_step(stages / folder, pid).translate((dx, 0, 0))
    scene.items = [i for i in scene.items if not i["name"].startswith("COLLAR_")]
    groups = {}

    def add(name, shape, group, mate=None):
        scene.items.append(dict(name=name, shape=shape, group=group))
        groups[name] = mate

    for name, (group, start, end, normal, radius, twin) in locations(scene).items():
        top, back, hardware = adapter(radius, twin)
        loc = horn_frame(start, end, normal)
        for label, shape in dict(top=top, back=back, **hardware).items():
            key = f"{name}/{label}"
            mate = None
            if label.endswith("_screw"):
                mate = f"{name}/{label.removesuffix('_screw')}_nut"
            if label.endswith("_nut"):
                mate = f"{name}/{label.removesuffix('_nut')}_screw"
            add(key, shape.moved(loc), group, mate)

    carrier = items["P45"]["shape"]
    carrier = carrier.cut(arc_clearance((-EX, EY), 12, 1.8, -21.8, 21.8, 92, 7)).clean()
    carrier = carrier.cut(arc_clearance((EX, EY), 12, 3.05, -21, 21, 91.9, 3.45)).clean()
    carrier = open_bore(carrier, (0, -12.25, 112.5), (1, 0, 0), 14)
    items["P45"]["shape"] = carrier

    # There is no room for the head of an M3 stop screw between the
    # original R14 sector and side wall. Add fixed faces at the ends.
    items["P36"]["shape"] = pitch_limit_blocks(items["P36"]["shape"])

    for tag, sx, rod_z, head_z, length in (("L", -1, 84.9, 97.8, 20), ("R", 1, 82.7, 92.1, 16)):
        xe, y = sx * EX, EY + 12
        rod = capsule((xe, y), (0, y), 3.85, rod_z - 1, 2)
        rod = rod.cut(pad(xe, y, rod_z - 2, 1.7, 4),
                      pad(0, y, rod_z - 2, 2.475, 4)).clean()
        items[f"P38_{tag}"]["shape"] = rod
        groups[f"P38_{tag}"] = None
        crank = items[f"P37_{tag}"]
        crank["shape"] = open_bore(crank["shape"], (xe, y, 90.5), (0, 0, 1), 8)
        spacer = sleeve((xe, y, rod_z + 1), (0, 0, 1), 89 - (rod_z + 1))
        screw, nuts = axial_fastener((xe, y, head_z), (0, 0, -1), length, (xe, y, rod_z - 1.2))
        add(f"yaw_{tag}_spacer", spacer, f"crank_{tag}")
        add(f"yaw_{tag}_screw", screw, f"crank_{tag}", f"yaw_{tag}_nuts")
        add(f"yaw_{tag}_nuts", nuts, f"crank_{tag}", f"yaw_{tag}_screw")

    pitch_rod = flat_rod(5.8, (-12.25, 112.5), (-12.25, 176.5))
    items["P46"]["shape"] = pitch_rod
    groups["P46"] = None
    screw, nuts = axial_fastener((-4, -12.25, 112.5), (1, 0, 0), 20, (7.25, -12.25, 112.5))
    add("pitch_lower_screw", screw, "pitch", "pitch_lower_nuts")
    add("pitch_lower_nuts", nuts, "pitch", "pitch_lower_screw")
    add("pitch_lower_spacer", sleeve((4, -12.25, 112.5), (1, 0, 0), 0.55), "pitch")

    # The left pivot retains the stock sleeve and insert. A 2 mm shim
    # makes the kit's M3x20 reach the same depth as the original M3x18.
    jaw_axis = (12.5, 56.25)
    left_head = (-79.9, *jaw_axis)
    left_screw = cylinder(1.5, left_head, (1, 0, 0), 20).fuse(
        cylinder(2.75, left_head, (-1, 0, 0), 3))
    add("jaw_left_pivot_screw", left_screw, "jaw")
    add("jaw_left_pivot_shim", sleeve(left_head, (1, 0, 0), 2), "jaw")
    screw, nuts = axial_fastener((77.9, *jaw_axis), (-1, 0, 0), 25, (59.0, *jaw_axis))
    add("jaw_right_pivot_screw", screw, "jaw", "jaw_right_pivot_nuts")
    add("jaw_right_pivot_nuts", nuts, "jaw", "jaw_right_pivot_screw")
    screw, nuts = axial_fastener((74.25, 26.5, 56.25), (-1, 0, 0), 25, (59.3, 26.5, 56.25))
    add("jaw_stop_screw", screw, "jaw", "jaw_stop_nuts")
    add("jaw_stop_nuts", nuts, "jaw", "jaw_stop_screw")

    right_rod = dogleg_lid_rod()
    for tag, sx, pid in (("L", -1, "P39_L"), ("R", 1, "P40_R")):
        rod = right_rod if sx > 0 else right_rod.mirror("YZ")
        items[f"P49_{tag}"]["shape"] = rod
        groups[f"P49_{tag}"] = None
        items["P36"]["shape"], items[pid]["shape"] = lid_limit_blocks(items["P36"]["shape"], items[pid]["shape"], sx)
        items[pid]["shape"], screw, nuts = lid_lower_pin(items[pid]["shape"], sx)
        add(f"lid_{tag}_screw", screw, f"lid_{tag}", f"lid_{tag}_nuts")
        add(f"lid_{tag}_nuts", nuts, f"lid_{tag}", f"lid_{tag}_screw")

    for key in ("P36", "P39_L", "P40_R"):
        pid = key.split("_")[0]
        previous_stage = "horn_adapters_new" if key == "P36" else "lid_hinges"
        added = items[key]["shape"].cut(from_step(stages / previous_stage, pid))
        add(f"{key}_added_material", added, items[key]["group"], key)

    cases = [dict(yaw=0, pitch=0, jaw=0, lid_L=0, lid_R=0)]
    cases.extend(dict(yaw=yaw, pitch=pitch, jaw=14, lid_L=left, lid_R=right)
                 for yaw, pitch, left, right in itertools.product((-20, 20), (-12, 12), (0, 50), (0, 50)))
    findings = []
    for index, pose in enumerate(cases):
        posed, _ = scene.pose(**pose)
        for item in posed:
            name = item["name"]
            if name not in groups:
                continue
            others = [(j["name"], j["shape"]) for j in posed
                      if j["name"] not in (name, groups[name])
                      and not j["name"].endswith("_added_material")
                      and not (index and item["group"] == j["group"])]
            for name2, volume in overlaps(item["shape"], others):
                findings.append(dict(pose=pose, a=name, b=name2, overlap_mm3=round(volume, 4)))
        print(f"Pose {index + 1}/{len(cases)}: {len(findings)} overlaps", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_LINKAGE_CLEARANCE" if not findings else "FAIL_LINKAGE_CLEARANCE",
                  poses=len(cases), physical_tested=False, findings=findings)
    (output / "linkage_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1
    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    for name in ("P36", "P45", "P37_L", "P38_L", "P39_L", "P40_R", "P46", "P49_L"):
        export_part(parts[name.split("_")[0]], items[name]["shape"], output)
    for index, (name, label, copies) in enumerate((
        ("yaw_L_spacer", "left_yaw_spacer", 1), ("yaw_R_spacer", "right_yaw_spacer", 1),
        ("pitch_lower_spacer", "pitch_spacer", 1),
        ("jaw_left_pivot_shim", "jaw_pivot_shim", 1),
    )):
        shape = next(i["shape"] for i in scene.items if i["name"] == name)
        rotation = [0, 90, 0] if name.startswith(("pitch", "lid", "jaw")) else [0, 0, 0]
        export_part(dict(id=f"A{21 + index}", name=label, qty=copies, print_rotation_xyz_deg=rotation), shape, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "stages", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.stages, args.output))
