"""Run transient simulations and hold the resulting waveforms."""

from __future__ import annotations

import bisect
import csv as _csv
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import com


@dataclass
class Simulation:
    """Waveforms sampled by Multisim from the registered probe outputs.

    ``time`` and every signal share one sample grid (seconds / volts or amps).
    """

    time: list[float]
    signals: dict[str, list[float]]
    meta: dict[str, Any] = field(default_factory=dict)
    csv_path: Path | None = None

    # ------------------------------------------------------------- building

    @classmethod
    def from_csv(cls, path: str | Path, meta: dict[str, Any] | None = None) -> "Simulation":
        path = Path(path)
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = _csv.reader(handle)
            header = next(reader)
            columns: dict[str, list[float]] = {name: [] for name in header}
            for row in reader:
                if not row:
                    continue
                for name, cell in zip(header, row):
                    columns[name].append(float(cell))
        if "time" not in columns:
            raise ValueError(f"{path}: missing 'time' column, header was {header!r}")
        time = columns.pop("time")
        return cls(time=time, signals=columns, meta=meta or {}, csv_path=path)

    # ------------------------------------------------------------ accessors

    def __len__(self) -> int:
        return len(self.time)

    @property
    def names(self) -> list[str]:
        return list(self.signals)

    def signal(self, name: str) -> list[float]:
        try:
            return self.signals[name]
        except KeyError:
            available = ", ".join(sorted(self.signals)) or "<none>"
            raise KeyError(f"unknown signal {name!r}; available: {available}") from None

    def at(self, name: str, t: float) -> float:
        """Linearly interpolated value of ``name`` at time ``t`` (seconds)."""
        values = self.signal(name)
        if not values:
            raise ValueError(f"signal {name!r} is empty")
        return _interpolate(self.time, values, t)

    def digital(self, name: str, t: float, threshold: float = 2.5) -> int:
        """Logic level at ``t``: 1 above ``threshold`` volts, else 0."""
        return 1 if self.at(name, t) > threshold else 0

    def edges(self, name: str, threshold: float = 2.5) -> list[tuple[float, int]]:
        """List of ``(time, new_level)`` pairs where the logic level changes."""
        values = self.signal(name)
        result: list[tuple[float, int]] = []
        previous = None
        for t, v in zip(self.time, values):
            level = 1 if v > threshold else 0
            if previous is not None and level != previous:
                result.append((t, level))
            previous = level
        return result


def _interpolate(times: list[float], values: list[float], t: float) -> float:
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    index = bisect.bisect_left(times, t)
    t0, t1 = times[index - 1], times[index]
    v0, v1 = values[index - 1], values[index]
    if t1 == t0:
        return v1
    ratio = (t - t0) / (t1 - t0)
    return v0 + (v1 - v0) * ratio


# ------------------------------------------------------------------ actions


def simulate(circuit: str | Path, duration: float, rate: float, *,
             csv: str | Path | None = None,
             only: Iterable[str] | None = None,
             timeout: float = 600.0) -> Simulation:
    """Run a transient analysis and return the probe waveforms.

    ``duration`` is in seconds, ``rate`` in samples per second. ``only`` keeps
    probe outputs whose names contain any of the given substrings.
    """
    circuit_path = Path(circuit).resolve()
    if not circuit_path.is_file():
        raise FileNotFoundError(f"circuit not found: {circuit_path}")
    if duration <= 0 or rate <= 0:
        raise ValueError("duration and rate must be positive")

    temporary = None
    if csv is None:
        handle, name = tempfile.mkstemp(prefix="msauto-", suffix=".csv")
        temporary = Path(name)
        os.close(handle)
        target = temporary
    else:
        target = Path(csv).resolve()

    args: list[Any] = [
        "simulate", circuit_path,
        "--duration", repr(float(duration)),
        "--rate", repr(float(rate)),
        "--csv", target,
        "--timeout", repr(float(timeout)),
    ]
    for needle in only or ():
        args.extend(["--only", needle])

    try:
        payload = com.run(*args, timeout=timeout + 60)
        return Simulation.from_csv(target, meta=payload)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def introspect(circuit: str | Path, *, timeout: float = 120.0) -> dict[str, Any]:
    """Return components, probe outputs and inputs of a circuit as a dict."""
    return com.run("introspect", Path(circuit).resolve(), timeout=timeout)


def export_netlist(circuit: str | Path, out: str | Path | None = None, *,
                   timeout: float = 120.0) -> dict[str, Any]:
    """Write Multisim's own netlist export and return ``{"path": ...}``."""
    args: list[Any] = ["netlist", Path(circuit).resolve()]
    if out is not None:
        args.extend(["--out", Path(out).resolve()])
    return com.run(*args, timeout=timeout)


def summarise(sim: Simulation) -> Mapping[str, tuple[float, float]]:
    """min/max per signal — handy for a quick sanity print."""
    return {name: (min(values), max(values)) for name, values in sim.signals.items() if values}
