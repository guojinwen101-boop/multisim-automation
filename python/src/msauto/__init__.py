"""msauto — script NI Multisim 14: build, simulate, verify.

Typical use::

    from msauto import simulate, Checks

    sim = simulate(r"C:\\circuits\\unit.ms14", duration=0.02, rate=20_000, csv="run.csv")
    chk = Checks(sim)
    chk.high("V(OutProbe1)", at=15e-3, message="relay driver active after 15 ms")
    chk.raise_for_failures()
"""

from .com import MsCtlError, find_msctl, run
from .netlist import LintIssue, lint
from .simulate import Simulation, introspect, simulate
from .template_pack import build_pack, list_parts, validate_pack
from .verify import CheckReport, Checks

__version__ = "0.1.0"

__all__ = [
    "CheckReport",
    "Checks",
    "LintIssue",
    "MsCtlError",
    "Simulation",
    "__version__",
    "build_pack",
    "find_msctl",
    "introspect",
    "lint",
    "list_parts",
    "run",
    "simulate",
    "validate_pack",
]
