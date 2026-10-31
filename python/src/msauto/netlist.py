"""Small linter for the SPICE dialect the Multisim builder accepts.

The dialect is ordinary SPICE with two Multisim-specific twists:

* digital ICs are written as lines starting with ``A`` (e.g. ``AU1 ... 74LS161``);
  only that prefix makes the builder embed the real element template;
* ``0`` is the ground net, but a bare ``1`` is **a net literally named "1"** —
  not logic high. Use ``vdd`` for logic high; a floating net "1" silently
  floats whole circuits and produces baffling simulation results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class LintIssue:
    level: str      # "error" or "warning"
    line: int       # 1-based line number
    message: str
    text: str = ""


def elements(text: str) -> Iterator[tuple[str, list[str]]]:
    """Yield ``(name, tokens)`` for every element line, skipping dot commands."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("."):
            continue
        tokens = line.split()
        yield tokens[0], tokens


def lint(text: str) -> list[LintIssue]:
    """Return problems found in ``text``, ordered by line number."""
    issues: list[LintIssue] = []
    seen: dict[str, int] = {}
    lines = text.splitlines()
    has_end = False

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.lower() == ".end":
            has_end = True
            continue
        if line.startswith("."):
            continue

        tokens = line.split()
        name = tokens[0]

        if name in seen:
            issues.append(LintIssue(
                "error", number,
                f"duplicate element name {name!r} (first seen on line {seen[name]})", line))
        else:
            seen[name] = number

        if name.startswith("A") and len(tokens) > 1:
            for token in tokens[1:]:
                if token == "1":
                    issues.append(LintIssue(
                        "warning", number,
                        "bare '1' is a net named \"1\" (floating), not logic high; "
                        "write vdd instead", line))
                    break

        if len(tokens) < 3:
            issues.append(LintIssue(
                "warning", number,
                f"element {name!r} has only {len(tokens)} token(s); "
                "expected at least a name and two nodes", line))

    if not has_end:
        issues.append(LintIssue("error", len(lines) or 1, "netlist has no .end line"))

    issues.sort(key=lambda issue: issue.line)
    return issues


def format_issues(issues: list[LintIssue]) -> str:
    return "\n".join(
        f"{i.level}:{i.line}: {i.message}" + (f"\n    {i.text}" if i.text else "")
        for i in issues
    )
