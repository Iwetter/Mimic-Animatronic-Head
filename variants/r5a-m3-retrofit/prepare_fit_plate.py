"""Prepare a small V5 hardware-fit slice using reusable printed clamps."""

import argparse
import json
import shutil
from pathlib import Path

from build_structural import export_part
from servo_clamps import box, candidate


def build(stages, output):
    for folder in ("STEP", "STL_REPRINT", "bom", "validation"):
        (output / folder).mkdir(parents=True, exist_ok=True)
    parts = []
    for stage, pid in (("mounts", "A10"), ("mounts", "A11"),
                       *[("horn_adapters_new", f"A{n}") for n in range(40, 46)]):
        source = next((stages / stage / "STL_REPRINT").glob(pid + "*_M3.stl"))
        target = output / "STL_REPRINT" / source.name
        shutil.copyfile(source, target)
        name = source.stem.removeprefix(pid + "_").removesuffix("_M3")
        parts.append(dict(id=pid, name=name, qty=1, stl=target.relative_to(output).as_posix(),
                          print_group="00_fit_coupons"))
    spec = dict(tip=(0, 0, 0), z=(0, 0, 1), y=(0, 1, 0), group="fixed")
    for pid, longitudinal in (("A90", False), ("A91", True)):
        origin = box(0, -9.2 if longitudinal else -8, -6.5, 22, 7.2 if longitudinal else 5, 3)
        clamp = candidate(spec, origin, -8, -1, 6 if longitudinal else 8.5, -8, 12, longitudinal)
        assert clamp is not None
        part = dict(id=pid, name="yaw_end_fit_seat" if longitudinal else "servo_tab_fit_seat",
                    qty=1, print_rotation_xyz_deg=[0, 0, 0], print_group="00_fit_coupons")
        part["stl"] = export_part(part, clamp.support, output)
        parts.append(part)
    (output / "bom/parts.json").write_text(
        json.dumps(dict(revision="V5-M3 hardware fit trial", parts=parts), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.stages, args.output)
