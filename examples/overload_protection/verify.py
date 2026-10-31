"""Simulate the built overload-protection unit and assert the specification.

    python verify.py out/overload_v1.ms14 --csv out/run.csv

The circuit was built with PROBES in a known order (see build.py), so probe
index i shows up as V(OutProbe) for i == 0 and V(OutProbe<i>) afterwards.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from msauto import CheckReport, simulate

# Must match build.py's PROBES order.
PROBES = ["q0", "q1", "q2", "ge1", "ge2",
          "sa1", "sb1", "sc1", "sd1", "se1", "sf1", "sg1",
          "sa2", "sg2", "l1a", "z2a", "coil1", "coil2"]

# (start ms, end ms, u, level1, level2, integer digit, fraction digit)
PLATEAUS = [
    (0.0, 1.0, 0, 0, 0, 0, 0),
    (5.0, 20.0, 2, 0, 0, 1, 0),     # one heavy pulse -> 1.0 A
    (25.0, 45.0, 3, 0, 0, 1, 5),    # one light pulse  -> 1.5 A
    (50.0, 70.0, 4, 1, 0, 2, 0),    # 2.0 A: relay 1 + lamp
    (75.0, 105.0, 5, 1, 1, 2, 5),   # 2.5 A: relay 2 + alarm
    (111.0, 118.0, 0, 0, 0, 0, 0),  # RESET
]
SEGMENTS = {0: set("abcdef"), 1: set("bc"), 2: set("abdeg"), 5: set("acdfg")}
LIT_MAX = 2.5   # a lit cathode sits near 1.6 V, a dark one near 5 V


def probe(index: int) -> str:
    return "V(OutProbe)" if index == 0 else f"V(OutProbe{index})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", help="the .ms14 produced by build.py")
    parser.add_argument("--csv", help="keep the raw waveforms here")
    parser.add_argument("--duration", type=float, default=0.119)
    parser.add_argument("--rate", type=float, default=20_000)
    args = parser.parse_args(argv)

    sim = simulate(args.circuit, args.duration, args.rate, csv=args.csv,
                   only=["V(OutProbe"])
    name = {probe_id: probe(i) for i, probe_id in enumerate(PROBES)}
    chk = CheckReport(sim)

    def state(t: float) -> int:
        return (sim.digital(name["q2"], t) * 4
                + sim.digital(name["q1"], t) * 2
                + sim.digital(name["q0"], t))

    for start, end, u, g1, g2, digit, fraction in PLATEAUS:
        at = ((start + end) / 2) * 1e-3   # seconds
        tag = f"t={at * 1e3:6.1f} ms"
        chk.expect_equal(state(at), u, f"{tag}: accumulator = {u * 0.5:.1f} A")
        chk.expect_digital(name["ge1"], at, g1, f"{tag}: level 1 (2.0 A) = {g1}")
        chk.expect_digital(name["ge2"], at, g2, f"{tag}: level 2 (2.5 A) = {g2}")

        lit = {seg for seg in "abcdefg" if sim.at(name[f"s{seg}1"], at) < LIT_MAX}
        chk.expect_equal(lit, SEGMENTS[digit], f"{tag}: integer display shows {digit}")
        lit_fraction = {seg for seg in "ag" if sim.at(name[f"s{seg}2"], at) < LIT_MAX}
        chk.expect_equal(lit_fraction, SEGMENTS[fraction] & set("ag"),
                         f"{tag}: fraction display shows {fraction}")

        chk.expect((sim.at(name["coil1"], at) < 1.0) == bool(g1),
                   f"{tag}: relay 1 {'closed' if g1 else 'released'}")
        chk.expect((sim.at(name["coil2"], at) < 1.0) == bool(g2),
                   f"{tag}: relay 2 {'closed' if g2 else 'released'}")
        chk.expect((sim.at(name["l1a"], at) > 1.6) == bool(g1),
                   f"{tag}: lamp {'on' if g1 else 'off'}")
        chk.expect((sim.at(name["z2a"], at) > 1.6) == bool(g2),
                   f"{tag}: alarm load {'on' if g2 else 'off'}")

    # The 96 ms pulse must not push the accumulator past 2.5 A.
    chk.expect_equal(state(100e-3), 5, "t= 100.0 ms: surplus pulse saturates at 2.5 A")
    # Step sizes: heavy +2 units, light +1 unit.
    chk.expect_equal(state(5e-3) - state(0.5e-3), 2, "heavy overload adds 1.0 A")
    chk.expect_equal(state(25e-3) - state(20e-3), 1, "light overload adds 0.5 A")

    ok = chk.report()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
