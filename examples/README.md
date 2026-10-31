# Examples

| Example | Needs | What it shows |
|---|---|---|
| `quickstart/inspect_circuit.py` | any `.ms14` with probes | introspect a circuit, run 10 ms, print min/max per probe |
| `overload_protection/` | a local template pack | full pipeline: netlist → schematic → simulation → 57 assertions |

The quickstart works on any circuit you already have:

```bat
python examples\quickstart\inspect_circuit.py C:\circuits\my_unit.ms14
```

The overload example builds a new schematic, so it needs the component
templates described in [`docs/template-packs.md`](../docs/template-packs.md).
Read its own README before trying to run it.
