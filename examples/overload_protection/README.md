# Example: overload thermal-simulation protection unit

A complete design built **from a netlist** and then verified by simulation.

## The specification

| Event | Effect |
|---|---|
| light overload (IL) | accumulate +0.5 A |
| heavy overload (IH) | accumulate +1.0 A |
| accumulated 2.0 A | relay 1 closes, overheat lamp on |
| accumulated 2.5 A | relay 2 closes, alarm on |
| extra pulses above 2.5 A | no further change (saturating) |
| reset (fault cleared) | relays release, lamp/alarm off, display 0.0 |

The total is displayed on two seven-segment digits (integer digit and the
0/5 fraction), driven by real 74LS48 decoders.

## How it is built

| Block | Parts |
|---|---|
| accumulator, 0.5 A per unit | 74LS161 (saturating next-state logic from 74LS00/74LS04 gates) |
| next-state select | 74LS157 |
| thresholds 4 and 5 units | 2 × 74LS85 |
| display | 2 × 74LS48, common-anode 7-segment, 220 Ω per segment |
| outputs | 2N2222 drivers, relay macros, diode+330 Ω lamp/alarm loads |
| input stimulus | three PULSE sources (stand-ins for the IL/IH/RESET buttons) |

`design.net` is the whole schematic; `build.py` registers the part templates,
places the parts at hand-picked coordinates and produces the `.ms14`.

## Run it

```bat
:: one-time: assemble a pack that contains d85 d48 d161 d157 n00 n04 seg q2222 diode
msauto pack build --base C:\my-base-pack --part C:\extracted\ls161 --out C:\ovp-pack
set MULTISIM_MCP_TEMPLATE_DIR=C:\ovp-pack
set MULTISIM_MCP_TEMPLATE_ONLY=1

python build.py --out out\overload_v1.ms14
python verify.py out\overload_v1.ms14 --csv out\run.csv
```

`verify.py` simulates 119 ms at 20 kHz and asserts 57 conditions: the state
sequence, both thresholds, segment patterns, relay coils, load currents, the
step sizes (+2 units for IH, +1 for IL) and saturation.

Expected tail:

```
...
57 passed, 0 failed
```

## Honest notes

* The lamp and alarm are **diode + 330 Ω loads**. Multisim 14.3's Lamp, LED and
  Buzzer symbols are interactive-only objects without SPICE models, so they
  cannot be validated by simulation. Replace them with the real symbols for the
  lab build and keep the electrical load here.
* The reset input is a signal (button / fault-cleared contact), not an automatic
  “current returned to normal” detector. Add a timeout circuit if the spec
  demands fully automatic clearing.
* The accumulator saturates; it does not decay. A true thermal model would add
  a discharge path.
* Source/part templates are extracted locally (see
  `docs/template-packs.md`); nothing NI-derived is in this repository.
