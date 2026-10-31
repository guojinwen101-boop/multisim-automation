# The netlist dialect

`msauto` does not simulate netlists directly. It hands them to the schematic
builder (multisim-mcp), which places real Multisim components and wires them up;
Multisim then simulates the resulting schematic. The input is therefore close
to SPICE but has a few non-obvious rules.

## Line format

```
NAME node1 node2 ... [value | model] [extra tokens]
```

* `0` is ground. `vdd` is the usual logic-high rail.
* `*` starts a comment; `.model`/`.end` behave as in SPICE.
* A bare token that names no source is simply **a net with that name**. There
  is no implicit “logic high”.

## Digital ICs: the `A` prefix

A digital part is written as

```
AU1 clk rst vdd vdd 0 n0 n1 n2m 0 q0 q1 q2 q3 rco 0 vdd 74LS161
```

The leading `A` is what tells the builder to embed the element template for the
part named in the last column. Without it, the part is created as a generic
XSUBN carrier and simulates as nothing.

Pin order is the part's SPICE template terminal order, which is often **not**
the pin-number order. Check your template, not the datasheet, when wiring.

## The floating-`1` trap

```
AU3 q0 1 q1 0 q2 vdd ...   <-- WRONG: net literally named "1"
AU3 q0 vdd q1 0 q2 vdd ... <-- correct
```

A bare `1` creates a net *named* `1`. Because nothing else connects to it, every
pin wired to it floats. The circuit still builds and simulates without an error;
it just produces garbage that looks like a logic bug. `msauto lint` flags this
on `A` lines.

## Registers and containers

* `XRK1 vdd coil1 vdd k1_out @RELAY RCOIL=400 VON=3 VOFF=1` — an adapter macro.
  Macros are expanded by the builder into primitive elements (`R…COIL`,
  `S…`, a `.model SW(...)`), so the netlist can stay readable.
* `VDD vdd 0 DC 5` — the supply is an ordinary source.
* Stimulus sources use SPICE `PULSE`/`SIN` syntax; time parameters accept
  `m`/`u`/`n` suffixes.

## Probes

Probe placement is builder configuration, not netlist syntax: pass
`probe_nets=[...]` to the builder and a probe is placed on each named net. The
resulting simulation names follow the index order (see
[com-notes.md](com-notes.md#probes-are-the-only-observation-channel)).

Only probed nets appear in the CSV. Probe the nets you intend to assert on —
especially in digital designs, where a missing probe shifts the index of every
later output.

## Layout hints

* `component_positions={"R1": [x, y], ...}` places parts on the sheet; omitted
  parts are auto-placed.
* `sheet_size=[width, height]` in the same units.
* The builder reports `crossings_per_wire`. Dense digital designs with explicit
  GND/VCC pins on every IC routinely score above 3.0; the default gate (2.0) is
  rarely reachable without hand placement. Treat it as a smell detector, not a
  hard requirement.
