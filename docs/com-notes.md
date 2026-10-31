# Multisim COM API — notes from the trenches

Everything here was confirmed against Multisim 14.3 on Windows 11 through
`TlbGen`-generated interop assemblies. Where behaviour looked like a bug, the
observed workaround is given.

## Object model

```
MultisimAppClass  (MultisimInterop)
  ├─ Connect() / Disconnect() / IsConnected / VersionInfo / LogFile
  └─ OpenFile(absolutePath) -> MultisimCircuit
       ├─ CircuitName, SimulationState, LastErrorMessage
       ├─ EnumComponents / EnumInputs / EnumOutputs
       ├─ SetOutputRequest, RunSimulation, StopSimulation, get_OutputReady
       ├─ GetOutputData, DoDCOperatingPoint
       ├─ ReportNetlist, GetCircuitImage
       └─ ReplaceComponent, SaveAs
```

The simulation members live on the **circuit** returned by `OpenFile`, not on
the application object. Early code that called `app.SetOutputRequest(...)` did
nothing at all.

`Connect()` launches a fresh `multisim.exe` each time. `Disconnect()` closes the
automation link; depending on version the process may stay around for a while,
so long batches can accumulate instances.

## Paths

* `OpenFile` needs an **absolute Windows path**. Relative paths raise
  “不是有效的路径名称” (invalid path name) on Chinese-locale installs.
* Keep the extension: `circuit.ms14`.
* `ReportNetlist(False, ExportText, outPath)` also wants an absolute-ish output
  path; it writes the file itself and returns a status string.

## Probes are the only observation channel

`EnumOutputs(SimulationIOAll)` lists outputs registered by probes in the
schematic, in the form `V(OutProbe)`, `V(OutProbe1)`, … plus `I(...)` variants.

* `SetOutputRequest("V(some_net)")` for an arbitrary net is **rejected** — the
  request completes but no data ever arrives, or the call fails outright. To
  observe a signal, place a probe in the schematic first.
* Probe `i` in the builder's `probe_nets` list (0-based) becomes `OutProbe` for
  `i == 0` and `OutProbe<i>` afterwards. A probe whose target has no valid wire
  point in the layout is skipped, but it still consumes its index — so a
  missing probe shifts everything after it.
* Probes attach by **position**: the builder places a transformer at
  M20/M21 coordinates and Multisim snaps it to the nearest wire. In a dense,
  overlapping layout a probe can silently attach to the wrong net (we once read
  a comparator output that was byte-for-byte the input clock). When a simulation
  contradicts the schematic, check the probe→net map before debugging logic.

## Running a simulation

```csharp
circ.SetOutputRequest(name, SimulationInterpolationLinear, rate, samples, false);
circ.RunSimulation(duration, false);              // seconds, not milliseconds
while (!circ.get_OutputReady(name)) Thread.Sleep(200);   // poll — the call is not blocking for data
var data = (double[,])circ.GetOutputData(name, out interp);
```

* `GetOutputData` returns a `double[,]` that is either `[2, n]` (channel-major)
  or `[n, 2]` (row-major). Check the dimensions instead of assuming.
* `RunSimulation` returns before the data is ready; polling `get_OutputReady`
  with a timeout is required. On failure read `circ.LastErrorMessage`.
* `StopSimulation()` aborts a run that will not finish (e.g. a model error).

## Interactive-only parts

In 14.3 the Buzzer, Lamp, LED, relay and switch symbols in the component
database are **interactive animation objects without a SPICE model**. The
simulator treats them as open circuits. If a design must be verified by
simulation, substitute electrical equivalents (diode + resistor, voltage-
controlled switch) and document the substitution — the symbol is not the model.

## Images

`GetCircuitImage(CircuitImagePNG, path)` works, but can throw a `COMException`
with a garbled message when called after a simulation has run. Export before
simulating if you need a screenshot.

## 32-bit only

The Multisim COM server is x86. The interop assembly and every process that
loads it must be 32-bit (`/platform:x86`). A 64-bit host cannot
`new MultisimAppClass()` successfully even though the type library imports
cleanly.
