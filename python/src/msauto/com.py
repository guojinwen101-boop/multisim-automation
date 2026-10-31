"""Locate and invoke the ``msctl`` COM driver.

``msctl`` is a small 32-bit .NET Framework program that talks to Multisim's
COM automation server. It prints one JSON object per run on stdout and
progress on stderr; this module is the thin, typed-ish wrapper around that.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence


class MsCtlError(RuntimeError):
    """Raised when msctl exits non-zero or reports an error payload."""

    def __init__(self, message: str, *, returncode: int | None = None,
                 payload: dict[str, Any] | None = None, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.payload = payload or {}
        self.stderr = stderr


def find_msctl() -> Path:
    """Return the path to msctl.exe.

    Resolution order: ``MSAUTO_MSCTL``, ``PATH``, then the repository layout
    (``csharp/bin/msctl.exe`` next to the installed package).
    """
    override = os.environ.get("MSAUTO_MSCTL")
    if override:
        path = Path(override)
        if not path.is_file():
            raise FileNotFoundError(f"MSAUTO_MSCTL points to a missing file: {path}")
        return path

    on_path = shutil.which("msctl") or shutil.which("msctl.exe")
    if on_path:
        return Path(on_path)

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "csharp" / "bin" / "msctl.exe"
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "msctl.exe not found. Build it with csharp/build.cmd, put it on PATH, "
        "or set MSAUTO_MSCTL to its full path."
    )


def run(*args: Any, timeout: float = 600.0, check: bool = True) -> dict[str, Any]:
    """Run msctl with the given arguments and return its JSON payload."""
    command = [str(find_msctl())] + [str(a) for a in args]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise MsCtlError(f"msctl timed out after {timeout:.0f}s: {' '.join(command)}") from exc

    payload = _parse_json(proc.stdout)
    if check and (proc.returncode != 0 or "error" in payload):
        detail = payload.get("detail") or payload.get("error") or proc.stderr.strip()
        raise MsCtlError(
            f"msctl failed (exit {proc.returncode}): {detail}",
            returncode=proc.returncode,
            payload=payload,
            stderr=proc.stderr,
        )
    return payload


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
                return value if isinstance(value, dict) else {"value": value}
            except json.JSONDecodeError:
                continue
    return {"raw": text}


def quote_all(items: Sequence[str]) -> list[str]:
    """Expand ``--only`` filters into repeated flag/value pairs."""
    out: list[str] = []
    for item in items:
        out.extend(["--only", item])
    return out
