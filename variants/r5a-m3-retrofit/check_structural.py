"""Check the new tooth lugs in the nominal R5a assembly and jaw sweep."""

import argparse
import json
import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cad_source"))
from motion import Scene
from build_structural import cylinder


def bounding_boxes_overlap(a, b):
    return all(
        getattr(a, k + "max") > getattr(b, k + "min") + 0.001
        and getattr(b, k + "max") > getattr(a, k + "min") + 0.001
        for k in "xyz"
    )


def check(baseline, output):
    scene = Scene(baseline)
    original = {item["name"]: item["shape"] for item in scene.items}
    edits = {}
    for path in sorted((output / "STEP").glob("*_M3.step")):
        pid = path.name.split("_")[0]
        edits[pid] = cq.importers.importStep(str(path)).val()
    for item in scene.items:
        if item["name"] in edits:
            item["shape"] = edits[item["name"]]

    neck_findings = []
    for z in (-48, -38):
        for x, direction, nut_start in ((-19, 1, -12.2), (19, -1, 9.8)):
            bolt = cylinder(1.5, (x, 21, z), (direction, 0, 0), 12)
            nut = (cq.Workplane("YZ").center(21, z)
                   .polygon(6, 5.5, circumscribed=True).extrude(2.4).val()
                   .translate((nut_start, 0, 0)))
            # Use the solid outer nut envelope. Check each hardware solid
            # against plastic independently of its intended thread contact.
            for part, shape in (("P01", original["P01"]), ("P03", edits["P03"])):
                for name, hardware in (("screw shank", bolt), ("nut envelope", nut)):
                    overlap = shape.intersect(hardware).Volume()
                    if overlap > 0.05:
                        neck_findings.append(dict(x=x, z=z, part=part, hardware=name,
                                                  overlap_mm3=overlap))

    added = {pid: edits[pid].cut(original[pid]) for pid in ("P42", "P43")}
    poses = [dict(jaw=angle) for angle in range(0, 15, 2)]
    poses.extend(dict(jaw=angle, yaw=yaw, pitch=pitch, lid_L=50, lid_R=50)
                 for angle in (0, 14) for yaw in (-20, 20) for pitch in (-12, 12))
    hits = []
    for pose in poses:
        items, _ = scene.pose(**pose)
        for pid, lug in added.items():
            moving_lug = lug.rotate((0, 12.5, 56.25), (1, 12.5, 56.25), pose["jaw"]) if pid == "P43" else lug
            bounds = moving_lug.BoundingBox()
            for item in items:
                if item["name"] == pid:
                    continue
                shape = item["shape"]
                if bounding_boxes_overlap(bounds, shape.BoundingBox()):
                    overlap = moving_lug.intersect(shape).Volume()
                    if overlap > 0.05:
                        hits.append(dict(pose=pose, lug=pid, part=item["name"], overlap_mm3=overlap))
    report = dict(status="PASS_SCOPED_CLEARANCE" if not hits and not neck_findings else "FAIL_SCOPED_CLEARANCE",
                  physical_tested=False, poses=len(poses), tooth_lug_findings=hits,
                  neck_fastener_findings=neck_findings,
                  scope="Added tooth lugs and four nominal neck screw shanks and nut envelopes. Other kit hardware and tool access are outside this check.")
    (output / "structural_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return bool(hits or neck_findings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sys.exit(check(args.baseline, args.output))
