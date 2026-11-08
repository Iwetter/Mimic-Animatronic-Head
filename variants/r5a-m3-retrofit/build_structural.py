"""Convert the fixed R5a hardware interfaces and export only changed parts.

The input is an R5a-E1 STEP build from cad_source/build_release.py.
This stage does not convert or validate the servo drives or running joints.
"""

import argparse
import csv
import json
from pathlib import Path

import cadquery as cq
import trimesh


def cylinder(radius, point, direction, length):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(*point), cq.Vector(*direction))


def open_bore(shape, point, direction, span):
    start = cq.Vector(*point) - cq.Vector(*direction) * (span / 2)
    return shape.cut(cylinder(1.7, start.toTuple(), direction, span)).clean()


def neck_nut_pocket(x, z):
    hexagon = cq.Workplane("YZ").center(21, z).polygon(6, 5.8, circumscribed=True)
    pocket = hexagon.extrude(3.2).val().translate((x, 0, 0))
    slot = cq.Workplane("XY").box(3.2, 10, 6.8).val().translate((x + 1.6, 26, z))
    return pocket.fuse(slot)


def structural_bores():
    """CAD centers from the existing R5a structural joints."""
    for arch, y in (("P25", -45), ("P26", 2), ("P27", 52)):
        yield (arch, "P28"), (0, y, 210), (0, 0, 1), 100
    for side, cheek, wall in ((-1, "P30", "P21"), (1, "P31", "P22")):
        yield ("P29", cheek), (side * 59, -57, 90), (0, 1, 0), 20
        yield ("P32", wall), (side * 68, -16, 60), (1, 0, 0), 28
    for x in (-8, 8):
        yield ("P29", "P32"), (x, -59, 67), (0, 1, 0), 20
    for teeth, carrier, z, offset, y in (
        ("P42", "P32", 56.6, 33, -40.5),
        ("P43", "P33", 35.5, 32, -41),
    ):
        for x in (-offset, offset):
            yield (teeth, carrier), (x, y, z), (0, 0, 1), 18


def reinforce_tooth_rows(shapes):
    # The stock tooth strips split at the original M1.6 holes if those
    # holes are widened directly. Add rear lugs and cut matching recesses
    # into their carriers while keeping the tooth positions.
    for teeth, carrier, bottom, thickness, offset, y in (
        ("P42", "P32", 56.0, 1.2, 33, -40.5),
        ("P43", "P33", 35.0, 1.0, 32, -41),
    ):
        for x in (-offset, offset):
            lug = cylinder(4.2, (x, y, bottom), (0, 0, 1), thickness)
            clearance = cylinder(4.4, (x, y, bottom - 0.05), (0, 0, 1), thickness + 0.1)
            shapes[teeth] = shapes[teeth].fuse(lug).clean()
            shapes[carrier] = shapes[carrier].cut(clearance).clean()


def fixed_hardware(contract):
    length_by_prefix = {
        "H_BASE_": 16, "H_PLATE_": 16, "H_ARCH_": 20, "H_CREST": 16,
        "H_FACE_": 20, "H_ZYG_P": 12, "H_MAX_P": 20, "H_MAX_FACE": 16,
        "H_TEETH_": 16, "H_EYE_DECK_": 20, "H_ZYG_ROOT_": 25,
        "H_DECK_": 20, "H_JAW_CRADLE_BASE": 16, "H_NECK_FLANGE": 20,
    }
    rows = []
    for item in contract["hardware"]:
        joint = item["id"]
        length = next((n for prefix, n in length_by_prefix.items() if joint.startswith(prefix)), None)
        if length is None:
            continue
        rows.append(dict(joint=joint, screws=f"M3x{length}", quantity=item["qty"],
                         original=item["size"], nuts=item["qty"], washers=2 * item["qty"]))
    rows.append(dict(joint="H_NECK_LOCK", screws="M3x12", quantity=4,
                     original="M3x45", nuts=4, washers=0))
    return rows


def export_part(part, solid, output):
    stem = f"{part['id']}_{part['name']}_M3"
    step = output / "STEP" / f"{stem}.step"
    stl = output / "STL_REPRINT" / f"{stem}.stl"
    cq.exporters.export(solid, str(step))
    bed_shape = solid
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), part["print_rotation_xyz_deg"]):
        if angle:
            bed_shape = bed_shape.rotate((0, 0, 0), axis, angle)
    bb = bed_shape.BoundingBox()
    bed_shape = bed_shape.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    cq.exporters.export(bed_shape, str(stl), tolerance=0.05, angularTolerance=0.1)
    mesh = trimesh.load_mesh(stl)
    zero_area = mesh.area_faces == 0
    if zero_area.any():
        mesh.update_faces(~zero_area)
        mesh.remove_unreferenced_vertices()
        mesh.export(stl)
    assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split()) == 1, stem
    assert abs(mesh.volume - solid.Volume()) / solid.Volume() < 0.005, stem
    assert all(extent <= 220 for extent in mesh.extents), stem
    return stl.relative_to(output).as_posix()


def build(baseline, output):
    contract = json.loads((baseline / "bom/parts.json").read_text())
    if contract["revision"] != "R5a-E1":
        raise ValueError("Use the R5a-E1 baseline STEP build.")
    parts = {p["id"]: p for p in contract["parts"]}
    requested_ids = {"P03"}
    for ids, _, _, _ in structural_bores():
        requested_ids.update(ids)
    original = {
        pid: cq.importers.importStep(str(baseline / parts[pid]["step"])).val()
        for pid in sorted(requested_ids)
    }
    changed = dict(original)
    reinforce_tooth_rows(changed)
    for ids, point, direction, span in structural_bores():
        for pid in ids:
            changed[pid] = open_bore(changed[pid], point, direction, span)
    for z in (-48, -38):
        for x in (-12.2, 9.0):
            changed["P03"] = changed["P03"].cut(neck_nut_pocket(x, z)).clean()

    for folder in ("STEP", "STL_REPRINT"):
        (output / folder).mkdir(parents=True, exist_ok=True)
    checks = []
    for pid, new in changed.items():
        old = original[pid]
        net_removed = old.Volume() - new.Volume()
        if abs(net_removed) < 0.001:
            continue
        assert new.isValid() and len(new.Solids()) == 1, pid
        added = new.cut(old).Volume()
        if pid not in ("P42", "P43"):
            assert added < 0.01, (pid, added)
        checks.append(dict(part=pid, copies=parts[pid]["qty"], net_removed_mm3=round(net_removed, 4),
                           added_mm3=round(added, 4), stl=export_part(parts[pid], new, output)))
        print(f"{pid}: valid edit, {net_removed:.2f} mm³ net removed, {added:.2f} mm³ added", flush=True)
    rows = fixed_hardware(contract)
    for name, values in (("fixed_joint_hardware.csv", rows), ("structural_reprint_list.csv", checks)):
        with (output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=values[0])
            writer.writeheader()
            writer.writerows(values)
    report = dict(revision="R5a-M3 development", status="STRUCTURAL CAD ONLY",
                  physical_tested=False, parts=checks)
    (output / "structural_geometry.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.baseline, args.output)
