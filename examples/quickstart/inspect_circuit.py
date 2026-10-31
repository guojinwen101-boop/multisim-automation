"""Introspect a circuit, simulate it briefly, report what came back.

    python inspect_circuit.py C:\\circuits\\unit.ms14

Works with any .ms14 that already has probes placed in the schematic.
"""

from __future__ import annotations

import sys
from pathlib import Path

from msauto import introspect, simulate


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    circuit = Path(argv[1])
    info = introspect(circuit)
    print(f"circuit : {info.get('circuit')}  ({info.get('version')})")
    print(f"parts   : {len(info.get('components', []))}")
    print(f"outputs : {len(info.get('outputs', []))}")
    for name in info.get("outputs", [])[:10]:
        print(f"  - {name}")

    sim = simulate(circuit, duration=0.01, rate=20_000, only=["V("])
    print(f"\nsimulated {len(sim)} samples over {sim.time[-1] * 1e3:.2f} ms")
    for name, values in sim.signals.items():
        print(f"  {name:24} min={min(values):.4g}  max={max(values):.4g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
