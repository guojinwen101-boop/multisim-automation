# msauto (Python)

Wraps the `msctl` COM driver, parses waveform CSVs, and turns circuit behaviour
into assertions.

```python
from msauto import simulate, Checks

sim = simulate(r"C:\circuits\unit.ms14", duration=0.02, rate=20_000, csv="run.csv")
chk = Checks(sim)
chk.expect_high("V(OutProbe1)", 15e-3, "comparator output high after 15 ms")
chk.expect_between("V(OutProbe2)", 15e-3, 4.5, 5.0, "load at 5 V")
chk.report()
chk.raise_for_failures()
```

## API

| Function | Purpose |
|---|---|
| `simulate(circuit, duration, rate, *, csv=None, only=None)` | Run a transient analysis. Returns a `Simulation`. |
| `introspect(circuit)` | Dict with components, probe outputs and inputs. |
| `export_netlist(circuit, out=None)` | Ask Multisim for its own netlist export. |
| `Simulation.at(name, t)` | Interpolated value (seconds). |
| `Simulation.digital(name, t, threshold=2.5)` | Logic level 0/1. |
| `Simulation.edges(name)` | `(time, level)` pairs where the level changes. |
| `Checks(sim)` | Assertion report: `expect`, `expect_equal`, `expect_digital`, `expect_between`, `expect_high`, `expect_low`, `report()`, `raise_for_failures()`. |
| `lint(text)` | Netlist linter (bare `1`, duplicate names, missing `.end`). |
| `template_pack.list_parts / validate_pack / build_pack` | Inspect and assemble local template packs. |

## CLI

```
msauto introspect <circuit.ms14>
msauto netlist    <circuit.ms14> [--out design.net]
msauto simulate   <circuit.ms14> --duration 0.02 --rate 20000 [--csv run.csv] [--only V(]
msauto lint       <netlist file | ->
msauto pack       list|validate|build ...
```

## Tests

```bat
pip install -e .[test]
pytest
```

The tests do not need Multisim — they exercise parsing, interpolation,
assertions, the linter and pack handling on synthetic data.
