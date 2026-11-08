"""Assemble the V5 M3 reprint manifest from the checked final parts."""

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path


REUSED = {"P01", "P20", "P35", "P90"}
FIT_PARTS = {"A10", "A11", "A40", "A41", "A42", "A43", "A44", "A45"}
STAGES = ("structural", "mounts", "lid_hinges", "yaw_clamps", "jaw_drive", "horn_adapters_new", "fixed")
EXTRAS = {
    "A10": 7, "A11": 2, "A12": 1, "A20": 2, "A21": 1, "A22": 1, "A23": 1, "A24": 1,
    "A30": 1, "A40": 1, "A41": 1, "A42": 1, "A43": 1, "A44": 2, "A45": 2,
}


def section(pid):
    if pid in {"P33", "P42", "P43", "P44", "A24", "A30"}:
        return "03_jaw"
    if pid in {"P34", "P36", "P37", "P38", "P39", "P40", "P45", "P46", "P49"}:
        return "02_eyes_and_lids"
    if pid.startswith("A") or pid == "P41":
        return "04_servo_mounts"
    return "01_frame"


def build(baseline, stages, final_stage, output):
    clearance = json.loads((final_stage / "linkage_clearance.json").read_text())
    if clearance["status"] != "PASS_SAMPLED_LINKAGE_CLEARANCE":
        raise ValueError("The integrated CAD checks must pass before the production plates are prepared.")
    data = json.loads((baseline / "bom/parts.json").read_text())
    original = {p["id"]: p for p in data["parts"]}
    sources = {}
    for stage in [*(stages / name for name in STAGES), final_stage]:
        for stl in (stage / "STL_REPRINT").glob("*_M3.stl"):
            sources[stl.name.split("_", 1)[0]] = stl
    assert set(sources) == (set(original) - REUSED) | set(EXTRAS), (set(original) - REUSED, set(sources))
    for name in ("STL_REPRINT", "STEP", "bom", "validation"):
        (output / name).mkdir(parents=True, exist_ok=True)
    print_rows, reprint_rows = [], []
    for pid, stl in sorted(sources.items()):
        part = original.get(pid, {})
        total = EXTRAS[pid] if pid in EXTRAS else part["qty"]
        on_fit_plate = int(pid in FIT_PARTS)
        remainder = total - on_fit_plate
        stl_path = output / "STL_REPRINT" / stl.name
        step = stl.parent.parent / "STEP" / stl.with_suffix(".step").name
        step_path = output / "STEP" / step.name
        shutil.copy2(stl, stl_path)
        shutil.copy2(step, step_path)
        name = stl.stem.removeprefix(pid + "_").removesuffix("_M3")
        if remainder:
            print_rows.append(dict(id=pid, name=name, qty=remainder,
                                   stl=stl_path.relative_to(output).as_posix(),
                                   step=step_path.relative_to(output).as_posix(), print_group=section(pid)))
        reprint_rows.append(dict(part=pid, name=name, total=total, on_fit_plate=on_fit_plate,
                                 on_remaining_plates=remainder, stl=stl_path.relative_to(output).as_posix()))
    with (output / "bom/reprints.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=reprint_rows[0])
        writer.writeheader()
        writer.writerows(reprint_rows)
    (output / "bom/parts.json").write_text(json.dumps(dict(revision="R5a-M3", parts=print_rows), indent=2))
    shutil.copyfile(final_stage / "linkage_clearance.json", output / "validation/linkage_clearance.json")

    fixed = list(csv.DictReader((stages / "structural/fixed_joint_hardware.csv").open()))
    moving = [
        ("Servo tab bridges", "M3x12", 10, 10, 0),
        ("Lid hinges", "M3x6", 4, 4, 0),
        ("Pitch carrier pivots", "M3x6", 2, 2, 0),
        ("Globe and crank shaft clamps", "M3x6", 4, 4, 0),
        ("Jaw horn clamp", "M3x8", 2, 2, 0),
        ("Yaw, pitch and lid horn plates", "M3x10", 4, 4, 0),
        ("Yaw horn shoulder pivot", "M3x8", 1, 1, 0),
        ("Pitch and lid horn shoulder pivots", "M3x6", 3, 3, 0),
        ("Left yaw tie", "M3x20", 1, 2, 0),
        ("Right yaw tie", "M3x16", 1, 2, 0),
        ("Lower pitch rod", "M3x20", 1, 2, 0),
        ("Lower lid shoulder pivots", "M3x8", 2, 2, 0),
        ("Left jaw pivot", "M3x20", 1, 1, 1),
        ("Right jaw pivot", "M3x25", 1, 2, 2),
        ("Jaw stop", "M3x25", 1, 2, 0),
    ]
    schedule = [{k: row[k] for k in ("joint", "screws", "quantity", "nuts", "washers")} for row in fixed]
    schedule += [dict(joint=joint, screws=size, quantity=quantity, nuts=nuts, washers=washers)
                 for joint, size, quantity, nuts, washers in moving]
    with (output / "bom/hardware_schedule.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=schedule[0])
        writer.writeheader()
        writer.writerows(schedule)
    tally = Counter()
    for row in schedule:
        tally[row["screws"]] += int(row["quantity"])
    tally["M3 plain nuts"] = sum(int(row["nuts"]) for row in schedule)
    tally["M3 washers"] = sum(int(row["washers"]) for row in schedule)
    (output / "bom/kit_totals.json").write_text(json.dumps(dict(hardware=tally), indent=2) + "\n")
    print(f"{len(sources)} designs. {sum(r['on_remaining_plates'] for r in reprint_rows)} remaining pieces.")
    print(dict(tally))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("baseline", "stages", "final_stage", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    build(args.baseline, args.stages, args.final_stage, args.output)
