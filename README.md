# msauto — drive NI Multisim 14 from the command line

**msauto** is a small, scriptable toolkit for NI Multisim 14.x on Windows. It talks
to Multisim through the official COM automation API and gives you a repeatable
loop that the mouse-driven UI cannot:

```
SPICE-like netlist ──► .ms14 schematic ──► headless transient run ──► CSV ──► assertions
```

No window stealing, no simulated clicks, no AutoHotkey. Multisim opens in the
background, runs, writes the data, and closes.

## What's in the box

| Piece | What it does |
|---|---|
| **`msctl`** (C#, .NET Framework 4, x86) | COM driver. Opens a circuit, reports its components/probes as JSON, exports the netlist, runs a transient simulation and writes a tidy CSV, swaps components, dumps a PNG. |
| **`msauto`** (Python 3.9+) | Wraps `msctl`, parses the CSV, and gives you waveform assertions (`Checks`) so a design can be verified by a test script instead of by eyeballing a grapher. Also contains a netlist linter and a template-pack builder. |
| **`docs/`** | The catalogue of COM quirks we hit the hard way — read this before debugging. |
| **`examples/`** | A quickstart (introspect + simulate any `.ms14`), and a full design example: an overload thermal-protection unit built from a netlist, simulated, and asserted. |

## Requirements

- Windows 10/11
- NI Multisim 14.x (licensed; the COM type library ships with it)
- .NET Framework 4 (`csc.exe` at `C:\Windows\Microsoft.NET\Framework\v4.0.30319`)
- Python 3.9+ (standard library only)

## Install

```bat
git clone https://github.com/<you>/multisim-automation.git
cd multisim-automation

:: 1) Build the COM interop assembly and msctl (32-bit — Multisim's COM server is x86)
csharp\build.cmd

:: 2) Install the Python package
pip install -e python
```

`build.cmd` locates `MSInterface.dll` in your own Multisim installation and
generates `Interop.MSInterface.dll` locally with `TlbGen` — no NI binaries are
stored in this repository. Set `MULTISIM_DIR` if auto-detection fails.

```bat
set MSAUTO_MSCTL=C:\path\to\msctl.exe   :: if msctl is not next to the repo or on PATH
```

## Quickstart

```bat
:: What probes and components does this circuit have?
msctl introspect C:\circuits\filter.ms14

:: Run 20 ms of transient at 20 kHz and export every probe to CSV
msctl simulate C:\circuits\filter.ms14 --duration 0.02 --rate 20000 --csv run.csv
```

```python
from msauto import simulate, Checks

sim = simulate(r"C:\circuits\filter.ms14", duration=0.02, rate=20_000, csv="run.csv")
print(sim.signals.keys())          # {'V(OutProbe1)': [...], ...}

chk = Checks(sim)
chk.equal(chk.digital(15e-3, "V(OutProbe1)"), 1, "comparator is high after 15 ms")
chk.between(15e-3, "V(OutProbe2)", 4.5, 5.0, "output stays at logic high")
chk.report()                       # prints PASS/FAIL lines
chk.raise_for_failures()           # AssertionError if anything failed
```

## The design example

`examples/overload_protection/` is a complete unit built **from a netlist**:
74LS161 accumulator + 74LS157 next-state mux + two 74LS85 comparators + two
74LS48 decoders + 7-segment displays + relay drivers. `build.py` turns
`design.net` into a new `.ms14`; `verify.py` asserts the whole spec (0.5 A per
light-overload pulse, 1.0 A per heavy one, relay 1 at 2.0 A, relay 2 at 2.5 A,
display digits, automatic limits) against a real Multisim simulation.

Building new schematics from a netlist is provided by the MIT-licensed
`multisim-mcp` builder (`multisim_mcp.schematic_builder`, distributed separately
by its authors — see `THIRD_PARTY_NOTICES.md`); msauto adds the CLI driver, the
template-pack workflow and the verification layer. See
`docs/template-packs.md` for the one-time local template extraction.

## Honest limitations

- **Windows + Multisim 14.x only.** The COM server is x86, so `msctl` is too.
- **Probes are position-based.** The COM API can enumerate probe outputs but
  rejects ad-hoc `V(<net>)` requests; every signal you want must have a probe
  placed in the schematic. Crowded or overlapping routing can make a probe
  snap to the wrong net — see `docs/troubleshooting.md`.
- **Interactive-only parts have no SPICE model.** In Multisim 14.3, the Buzzer,
  Lamp, LED and Relay symbols are animation-only; they do not simulate. Use
  electrical stand-ins (diode + resistor, voltage-controlled switch) if you need
  real waveforms, and document the substitution.
- **Auto-placement is functional, not pretty.** The builder's layout validator
  scores crossings per wire; dense digital designs with explicit GND/VCC pins
  frequently exceed the default gate. Tidy the power rails by hand if you care
  about how the schematic looks.
- **Component templates are extracted locally.** Nothing derived from NI's
  libraries is distributed here. See the template policy below.

## Template policy

Multisim's component templates are licensed NI content. This repository contains
**code only**. To build schematics you generate a template pack from your own
licensed installation:

```bat
python tools\bootstrap_local_component_pack.py --output C:\my-pack
set MULTISIM_MCP_TEMPLATE_DIR=C:\my-pack
```

That pack stays on your machine and must never be committed or redistributed.
The repository `.gitignore` excludes every common template-pack location so an
accidental `git add .` cannot publish it.

## License

MIT — see `LICENSE`. Not affiliated with or endorsed by National Instruments.
Multisim is a trademark of National Instruments. Third-party notices in
`THIRD_PARTY_NOTICES.md`.
