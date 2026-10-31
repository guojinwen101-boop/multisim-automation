"""Waveform assertions.

``Checks`` turns a :class:`~msauto.simulate.Simulation` into a small test
report so a circuit's behaviour can be verified by a script instead of by
staring at a grapher::

    chk = Checks(sim)
    chk.expect_digital("V(OutProbe1)", 15e-3, 1, "relay driver active after 15 ms")
    chk.expect_between("V(OutProbe2)", 15e-3, 4.5, 5.0, "load stays at 5 V")
    chk.report()
    chk.raise_for_failures()
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO

from .simulate import Simulation


class CheckFailure(AssertionError):
    """Raised by :meth:`CheckReport.raise_for_failures`."""


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str
    detail: str = ""


class CheckReport:
    def __init__(self, sim: Simulation, *, threshold: float = 2.5,
                 stream: TextIO | None = None) -> None:
        self.sim = sim
        self.threshold = threshold
        self.stream = stream
        self.results: list[CheckResult] = []

    # ------------------------------------------------------------ read side

    def at(self, name: str, t: float) -> float:
        return self.sim.at(name, t)

    def digital(self, name: str, t: float, threshold: float | None = None) -> int:
        return self.sim.digital(name, t, self.threshold if threshold is None else threshold)

    # ----------------------------------------------------------- assertions

    def expect(self, condition: bool, message: str, detail: str = "") -> CheckResult:
        result = CheckResult(bool(condition), message, "" if condition else detail)
        self.results.append(result)
        return result

    def expect_equal(self, actual, expected, message: str) -> CheckResult:
        return self.expect(actual == expected, message, f"expected {expected!r}, got {actual!r}")

    def expect_between(self, name: str, at: float, low: float, high: float,
                       message: str) -> CheckResult:
        value = self.at(name, at)
        return self.expect(
            low <= value <= high,
            message,
            f"{name}@ {at * 1e3:.3f} ms = {value:.6g}, expected {low}..{high}",
        )

    def expect_digital(self, name: str, at: float, level: int, message: str,
                       threshold: float | None = None) -> CheckResult:
        value = self.at(name, at)
        actual = self.digital(name, at, threshold)
        return self.expect(
            actual == level,
            message,
            f"{name}@ {at * 1e3:.3f} ms = {value:.6g} V (logic {actual}), expected logic {level}",
        )

    def expect_high(self, name: str, at: float, message: str) -> CheckResult:
        return self.expect_digital(name, at, 1, message)

    def expect_low(self, name: str, at: float, message: str) -> CheckResult:
        return self.expect_digital(name, at, 0, message)

    # -------------------------------------------------------------- outcome

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.ok]

    @property
    def ok(self) -> bool:
        return not self.failures

    def report(self, stream: TextIO | None = None) -> bool:
        """Print every check as PASS/FAIL plus a summary; return True if all passed."""
        stream = stream or self.stream or sys.stdout
        for result in self.results:
            status = "PASS" if result.ok else "FAIL"
            detail = f"  ({result.detail})" if result.detail else ""
            print(f"[{status}] {result.message}{detail}", file=stream)
        failed = len(self.failures)
        print(f"{len(self.results) - failed} passed, {failed} failed", file=stream)
        return failed == 0

    def raise_for_failures(self) -> None:
        if not self.failures:
            return
        lines = [f"{r.message} ({r.detail})" if r.detail else r.message for r in self.failures]
        raise CheckFailure(f"{len(lines)} check(s) failed:\n  " + "\n  ".join(lines))


# Friendly alias used in the README.
Checks = CheckReport
