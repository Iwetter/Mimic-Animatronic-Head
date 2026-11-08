"""Check printed pitch and lid stop contact past the commanded range."""

import argparse
import json
from pathlib import Path

from build_linkages import EY, axial_fastener, from_step


def check(stages, final, output):
    deck = from_step(final, "P36").cut(from_step(stages / "fixed", "P36"))
    evidence = []
    for pid, before, low, high in (
        ("P45", "horn_adapters_new", (-12, -17), (12, 17)),
        ("P39", "lid_hinges", (0, -6), (50, 56)),
        ("P40", "lid_hinges", (0, -6), (50, 56)),
    ):
        tab = from_step(final, pid).cut(from_step(stages / before, pid))
        for within, beyond in (low, high):
            def contact(angle):
                return deck.intersect(tab.rotate((0, EY, 112.5), (1, EY, 112.5), angle)).Volume()

            within_volume, beyond_volume = contact(within), contact(beyond)
            entry = dict(part=pid, command_limit_deg=within, test_angle_deg=beyond,
                         at_command_overlap_mm3=round(within_volume, 4),
                         past_limit_overlap_mm3=round(beyond_volume, 4),
                         pass_stop=within_volume < 0.05 < beyond_volume)
            evidence.append(entry)
            print(entry, flush=True)
    wall = from_step(stages / "fixed", "P22")
    bolt, _ = axial_fastener((74.25, 26.5, 56.25), (-1, 0, 0), 25, (59.3, 26.5, 56.25))
    for within, beyond in ((0, -3), (14, 18)):
        def jaw_contact(angle):
            return wall.intersect(bolt.rotate((0, 12.5, 56.25), (1, 12.5, 56.25), angle)).Volume()

        nominal, past = jaw_contact(within), jaw_contact(beyond)
        entry = dict(part="Jaw stop screw", command_limit_deg=within, test_angle_deg=beyond,
                     at_command_overlap_mm3=round(nominal, 4),
                     past_limit_overlap_mm3=round(past, 4), pass_stop=nominal < 0.05 < past)
        evidence.append(entry)
        print(entry, flush=True)
    ok = all(row["pass_stop"] for row in evidence)
    output.write_text(json.dumps(dict(status="PASS_STOP_CONTACT" if ok else "FAIL_STOP_CONTACT",
                                     physical_tested=False, stops=evidence), indent=2) + "\n")
    return int(not ok)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("stages", "final", "output"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    raise SystemExit(check(args.stages, args.final, args.output))
