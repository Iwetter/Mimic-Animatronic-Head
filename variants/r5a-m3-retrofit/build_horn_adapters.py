"""Sandwich the OEM yaw, pitch and lid horns while keeping their link radii.

The M3 link pin seats in a captured nut above the original horn arm. A
printed shoulder sets running clearance and keeps the screw off the arm.
"""

import argparse
import json
from pathlib import Path

import cadquery as cq

from build_structural import cylinder, export_part
from check_structural import Scene
from servo_clamps import box, overlaps


EY = -36.25
CLAMP_OFFSET = 9.0


def horn_frame(start, end, normal):
    start = cq.Vector(*start)
    radial = cq.Vector(*end) - start
    return cq.Location(cq.Plane(start, radial.normalized(), cq.Vector(*normal)))


def pad(x, y, z, radius, height):
    return cylinder(radius, (x, y, z), (0, 0, 1), height)


def capsule(start, end, radius, bottom, height):
    start = cq.Vector(start[0], start[1], bottom + height / 2)
    end = cq.Vector(end[0], end[1], bottom + height / 2)
    vec = end - start
    body = cq.Workplane(cq.Plane((start + end) / 2, vec.normalized(), cq.Vector(0, 0, 1)))
    body = body.box(vec.Length, 2 * radius, height).val()
    return body.fuse(pad(start.x, start.y, bottom, radius, height),
                     pad(end.x, end.y, bottom, radius, height)).clean()


def hex_nut(x, y, z, width, height):
    return cq.Workplane("XY", origin=(x, y, z)).polygon(6, width, circumscribed=True).extrude(height).val()


def adapter(radius, twin):
    # Put the single clamp screw past the horn tip and away from the
    # swept rod. An outer heel reacts the tightening load.
    bolt_x = radius + CLAMP_OFFSET
    top = pad(radius, 0, 1, 4.35, 3.4)
    top = top.fuse(capsule((bolt_x, 0), (radius, 0), 3.5, 1, 2.8)).clean()
    back = capsule((bolt_x, 0), (radius, 0), 3.5, -3, 2)
    hardware = {}
    top = top.fuse(box(bolt_x + 2.5, 0, 0.08, 1.3, 2.4, 2.16)).clean()
    drill = pad(bolt_x, 0, -4, 1.7, 10)
    top = top.cut(drill).clean()
    back = back.cut(drill).clean()
    hardware["clamp_screw"] = pad(bolt_x, 0, -3, 1.5, 10).fuse(pad(bolt_x, 0, -6, 2.75, 3))
    hardware["clamp_nut"] = hex_nut(bolt_x, 0, 3.8, 5.5, 2.4)
    for y in (-3.1, 3.1):
        top = top.fuse(box(radius - 1.5, y, 0.65, 3, 0.8, 0.8)).clean()

    shoulder_length = 4.8 if twin else 2.8
    top = top.fuse(pad(radius, 0, 4.38, 2.35, shoulder_length + 0.02)).clean()
    pocket = hex_nut(radius, 0, 1.2, 5.8, 2.6)
    slot = box(radius + 2.4, 0, 2.5, 4.8, 6.55, 2.6)
    top = top.cut(pocket.fuse(slot), pad(radius, 0, 1.18, 1.7, 10)).clean()
    hardware["pivot_nut"] = hex_nut(radius, 0, 1.2, 5.5, 2.4)
    seat = 4.4 + shoulder_length
    shank_length = 8 if twin else 6
    hardware["pivot_screw"] = pad(radius, 0, seat - shank_length, 1.5, shank_length).fuse(
        pad(radius, 0, seat, 2.75, 3))
    assert all(s.isValid() and len(s.Solids()) == 1 for s in (top, back))
    return top, back, hardware


def locations(scene):
    lid_y, lid_z = scene.contract["servos"]["SG90_CH4_lid_R"]["tip"][1:]
    return {
        "yaw": ("yawhorn", (0, EY, 90.5), (0, EY + 12, 90.5), (0, 0, -1), 12, True),
        "pitch": ("pitchhorn", (0, 1.75, 176.5), (0, -12.25, 176.5), (1, 0, 0), 14, False),
        "lid_L": ("lidhorn_L", (-55.5, lid_y, lid_z), (-55.5, -26.45, 186), (-1, 0, 0), 10, False),
        "lid_R": ("lidhorn_R", (55.5, lid_y, lid_z), (55.5, -26.45, 186), (1, 0, 0), 10, False),
    }


def build(baseline, mounts, output, hinges):
    scene = Scene(baseline)
    # The old link center planes will move to the new adapter shoulders.
    # Test the adapter envelopes against all other existing components first.
    scene.items = [i for i in scene.items if not i["group"].startswith(("yawlink", "pitchrod", "lidrod"))]
    for item in scene.items:
        if hinges and item["name"] in ("P36", "P45", "P39_L", "P40_R"):
            pid = item["name"].split("_")[0]
            path = next((hinges / "STEP").glob(pid + "*_M3.step"))
            item["shape"] = cq.importers.importStep(str(path)).val()
        elif item["name"] in ("P41", "P44", "P45"):
            path = next((mounts / "STEP").glob(item["name"] + "*_M3.step"))
            item["shape"] = cq.importers.importStep(str(path)).val()
    names = set()
    carrier = next(i for i in scene.items if i["name"] == "P45")
    eye_deck = next(i for i in scene.items if i["name"] == "P36")
    # The yaw adapter passes the rear corner of each inner lid prong
    # at negative pitch. Keep the hinge and its upper prong intact.
    for side in (-1, 1):
        relief = box(side * 11.46, -35.92, 87.5, 1.45, 1.24, 4.0)
        eye_deck["shape"] = eye_deck["shape"].cut(relief).clean()
    assert eye_deck["shape"].isValid() and len(eye_deck["shape"].Solids()) == 1
    for name, (group, start, end, normal, radius, twin) in locations(scene).items():
        top, back, hardware = adapter(radius, twin)
        loc = horn_frame(start, end, normal)
        if twin:
            clearance = pad(radius + CLAMP_OFFSET, 0, -6.35, 3.1, 3.65).moved(loc)
            cutters = [clearance.rotate((0, EY, 90.5), (0, EY, 91.5), angle)
                       for angle in range(-21, 22, 3)]
            backing_clearance = capsule((radius + CLAMP_OFFSET, 0), (radius, 0),
                                        3.8, -3.3, 2.3).moved(loc)
            cutters.extend(backing_clearance.rotate((0, EY, 90.5), (0, EY, 91.5), angle)
                           for angle in range(-21, 22, 3))
            carrier["shape"] = carrier["shape"].cut(*cutters).clean()
            assert carrier["shape"].isValid() and len(carrier["shape"].Solids()) == 1
        for label, solid in dict(top=top, back=back, **hardware).items():
            key = f"{name}/{label}"
            scene.items.append(dict(name=key, shape=solid.moved(loc), group=group))
            names.add(key)

    cases = [dict(yaw=0, pitch=0, lid_L=0, lid_R=0)]
    for yaw in (-20, 20):
        for pitch in (-12, 12):
            for lid in (0, 25, 50):
                cases.append(dict(yaw=yaw, pitch=pitch, lid_L=lid, lid_R=lid))
    findings = []
    for index, pose in enumerate(cases):
        items, _ = scene.pose(**pose)
        for item in items:
            key = item["name"]
            if key not in names:
                continue
            others = []
            for other in items:
                name = other["name"]
                if name == key:
                    continue
                if key.rsplit("_", 1)[0] == name.rsplit("_", 1)[0] and {
                    key.rsplit("_", 1)[1], name.rsplit("_", 1)[1]
                } == {"screw", "nut"}:
                    continue
                if index and other["group"] == item["group"]:
                    continue
                others.append((name, other["shape"]))
            for name, volume in overlaps(item["shape"], others):
                findings.append(dict(pose=pose, a=key, b=name, overlap_mm3=round(volume, 4)))
        print(f"Pose {index + 1}/{len(cases)}: {len(findings)} overlaps", flush=True)

    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_HORN_ENVELOPES" if not findings else "FAIL_HORN_ENVELOPES",
                  poses=len(cases), physical_tested=False, findings=findings,
                  scope="Nominal horn clamps and screws. Redesigned pushrods are outside this check.")
    (output / "horn_adapter_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1
    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    export_part(parts["P45"], carrier["shape"], output)
    export_part(parts["P36"], eye_deck["shape"], output)
    for index, (name, radius, twin, qty) in enumerate((
        ("yaw", 12, True, 1), ("pitch", 14, False, 1), ("lid", 10, False, 2),
    )):
        top, back, _ = adapter(radius, twin)
        for j, (label, shape) in enumerate((("adapter", top), ("backplate", back))):
            export_part(dict(id=f"A{40 + 2 * index + j}", name=f"{name}_{label}", qty=qty,
                             print_rotation_xyz_deg=[0, 0, 0]), shape, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "mounts", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--hinges", type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.mounts, args.output, args.hinges))
