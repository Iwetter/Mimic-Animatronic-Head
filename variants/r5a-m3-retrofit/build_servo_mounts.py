"""Build and check the V5 M3 servo clamps against the R5a mechanism."""

import argparse
import itertools
import json
from pathlib import Path

import cadquery as cq

from build_structural import export_part
from check_structural import Scene
from servo_clamps import candidate, overlaps


# One clamp on each end of the servo. The side is in the servo's local frame.
# The original flange seating face and spline position are preserved.
PLACEMENT = {
    "MG90S_CH0_yaw": ("P45", -6.5, (-1, 1)),
    "MG90S_CH1_jaw": ("P44", -7.5, (-1, 1)),
    "MG90S_CH2_pitch": ("P41", -10.0, (-1, -1)),
    "SG90_CH3_lid_L": ("P41", -8.0, (1, -1)),
    "SG90_CH4_lid_R": ("P41", -8.0, (-1, 1)),
}


def longitudinal_tab(servo, tab_y):
    return servo == "MG90S_CH0_yaw" or (tab_y == -8 and servo == "MG90S_CH1_jaw")


def tab_geometry(servo, tab_y):
    if servo == "MG90S_CH0_yaw" and tab_y == 20:
        return 10.1, "A12", True
    if longitudinal_tab(servo, tab_y):
        return 6, "A11", True
    return 8.5, "A10", False


def build(baseline, output):
    scene = Scene(baseline)
    parts = {p["id"]: p for p in json.loads((baseline / "bom/parts.json").read_text())["parts"]}
    original = {item["name"]: item["shape"] for item in scene.items}
    edited = {pid: original[pid] for pid in ("P45", "P44", "P41")}
    added_names = set()
    print_clips = {}
    placements = []
    for servo, (pid, backing, sides) in PLACEMENT.items():
        spec = scene.contract["servos"][servo]
        for tab_y, side in zip((-8, 20), sides):
            bolt_offset, clip_id, longitudinal = tab_geometry(servo, tab_y)
            clamp = candidate(spec, edited[pid], tab_y, side, bolt_offset, backing, 12, longitudinal)
            if clamp is None:
                raise ValueError((servo, tab_y, "invalid clamp"))
            support = clamp.support
            if servo == "MG90S_CH0_yaw" and tab_y == 20:
                # Existing rear carrier boss meets the clip nose. Clear just
                # that pocket. The outer heel pad stays at the same height.
                support = support.cut(clamp.clip).clean()
                for axis in ((0, 0, 0.15), (0, 0.15, 0), (0, -0.15, 0)):
                    support = support.cut(clamp.clip.translate(axis)).clean()
            assert support.isValid() and len(support.Solids()) == 1, (servo, tab_y)
            edited[pid] = support
            print_clips.setdefault(clip_id, clamp.clip_print)
            prefix = f"{servo}_tab_{tab_y}"
            for name, shape in (("bridge", clamp.clip), ("screw", clamp.screw), ("nut", clamp.nut)):
                key = f"{prefix}_{name}"
                scene.items.append(dict(name=key, shape=shape, group=clamp.group))
                added_names.add(key)
            placements.append(dict(servo=servo, support=pid, tab_local_y_mm=tab_y,
                                   bolt_offset_mm=bolt_offset * side, longitudinal=longitudinal,
                                   screw="M3x12", clip=clip_id))

    # Only added support material can cause new overlaps with other parts.
    # The hardware must also clear the full revised support.
    for item in scene.items:
        if item["name"] in edited:
            item["shape"] = edited[item["name"]]
            key = f"{item['name']}_new_material"
            scene.items.append(dict(name=key, shape=item["shape"].cut(original[item["name"]]),
                                    group=item["group"]))
            added_names.add(key)

    cases = [dict(label="neutral")]
    for yaw, pitch, jaw, lid in itertools.product((-20, 20), (-12, 12), (0, 14), (0, 50)):
        cases.append(dict(label=f"{yaw}/{pitch}/{jaw}/{lid}", yaw=yaw, pitch=pitch,
                          jaw=jaw, lid_L=lid, lid_R=lid))
    findings = []
    for case in cases:
        pose = {k: v for k, v in case.items() if k != "label"}
        items, _ = scene.pose(**pose)
        for item in items:
            key = item["name"]
            if key not in added_names:
                continue
            candidates = []
            for other in items:
                name = other["name"]
                if name == key or name.endswith("_new_material"):
                    continue
                if key.endswith("_new_material") and name == key.removesuffix("_new_material"):
                    continue
                # The shank and its own nut are threaded together.
                if key.rsplit("_", 1)[0] == name.rsplit("_", 1)[0] and {
                    key.rsplit("_", 1)[1], name.rsplit("_", 1)[1]
                } == {"screw", "nut"}:
                    continue
                if case["label"] != "neutral" and item["group"] == other["group"]:
                    continue
                candidates.append((name, other["shape"]))
            for name, volume in overlaps(item["shape"], candidates):
                findings.append(dict(pose=case["label"], a=key, b=name, overlap_mm3=round(volume, 4)))
        print(case["label"], len(findings), flush=True)

    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="PASS_SAMPLED_SERVO_MOUNT_CLEARANCE" if not findings else "FAIL_SERVO_MOUNT_CLEARANCE",
                  physical_tested=False, poses=len(cases), findings=findings, placements=placements)
    (output / "servo_mount_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    if findings:
        return 1

    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(exist_ok=True)
    for pid, shape in edited.items():
        export_part(parts[pid], shape, output)
    for pid, shape in print_clips.items():
        clip = dict(id=pid, name="servo_tab_bridge", qty=sum(p["clip"] == pid for p in placements),
                    print_rotation_xyz_deg=[0, 0, 0])
        export_part(clip, shape, output)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.baseline, args.output))
