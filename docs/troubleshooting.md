# Troubleshooting

## `msctl introspect` fails with “invalid path name”

Use an absolute Windows path. Relative paths are rejected by `OpenFile` even
when the working directory is right.

## `new MultisimAppClass()` throws on a 64-bit build

The COM server is x86. Compile everything with `/platform:x86` and run the
32-bit process. `build.cmd` already does this.

## Simulation ends with `ready: false`

`msctl` prints `LastErrorMessage` to stderr. Common causes:

* a component template is missing or malformed — the part simulates as an open
  circuit and the solver may still “finish”, so also check whether the signals
  are plausible;
* a model card lost its line breaks (see `template-packs.md`);
* the duration is far longer than needed and the timeout expired — raise
  `--timeout`.

`<circuit>.sim.log` next to the `.ms14` holds Multisim's own log.

## Every probe output is 0 or has no signal

* The schematic has no probes. `EnumOutputs` is empty and `msctl simulate`
  exits with code 4.
* A probe was skipped (no wire at its coordinates), shifting all later probe
  names by one.

## Signals are plausible but wrong

* A digital IC line used a bare `1` instead of `vdd` — run
  `msauto lint design.net`.
* A probe attached to the wrong net because the layout overlaps. Compare the
  waveform with a known-good node; the builder's `geometry` output lists wire
  segments per net if you need to investigate.
* A part is missing from the template pack and got substituted by an empty
  carrier.

## Absurd currents (hundreds of amps)

The 7-segment/LED models in some packs have no internal series resistance. Put
a 220 Ω resistor in series with every segment; expected values are then around
1.6 V across the lit LED and ~10 mA.

## Multisim windows accumulate

Each `Connect()` starts an instance and `Disconnect()` does not always terminate
it. Close stray `multisim.exe` processes between long batches.

## `msctl.exe not found`

Build it (`csharp/build.cmd`), put `csharp/bin` on `PATH`, or set
`MSAUTO_MSCTL` to its absolute path.
