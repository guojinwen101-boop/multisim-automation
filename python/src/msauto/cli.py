"""Command-line entry point: ``msauto <command> ...``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, com, template_pack
from .netlist import format_issues, lint
from .simulate import export_netlist, introspect as introspect_circuit, simulate as run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="msauto",
        description="Script NI Multisim 14: build, simulate and verify circuits.",
    )
    parser.add_argument("--version", action="version", version=f"msauto {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("introspect", help="list components and probe outputs of a .ms14")
    p.add_argument("circuit")
    p.add_argument("--timeout", type=float, default=120.0)

    p = sub.add_parser("netlist", help="export the netlist Multisim builds for a .ms14")
    p.add_argument("circuit")
    p.add_argument("--out")
    p.add_argument("--timeout", type=float, default=120.0)

    p = sub.add_parser("simulate", help="run a transient analysis and write a CSV")
    p.add_argument("circuit")
    p.add_argument("--duration", type=float, required=True, help="seconds of simulated time")
    p.add_argument("--rate", type=float, required=True, help="samples per second")
    p.add_argument("--csv", help="output CSV (a temporary file is used otherwise)")
    p.add_argument("--only", action="append", default=[],
                   help="keep probe outputs containing this substring (repeatable)")
    p.add_argument("--timeout", type=float, default=600.0)

    p = sub.add_parser("lint", help="check a netlist for the usual Multisim pitfalls")
    p.add_argument("netlist", help="a .net / .cir text file, or '-' for stdin")
    p.add_argument("--strict", action="store_true", help="exit 1 on warnings too")

    pack = sub.add_parser("pack", help="inspect or assemble local template packs")
    pack_sub = pack.add_subparsers(dest="pack_command", required=True)
    p = pack_sub.add_parser("validate", help="report missing symbol/port files")
    p.add_argument("directory")
    p = pack_sub.add_parser("build", help="copy a base pack and overlay part templates")
    p.add_argument("--base", required=True)
    p.add_argument("--part", action="append", default=[], help="repeatable part directory")
    p.add_argument("--out", required=True)
    p.add_argument("--overwrite", action="store_true")
    p = pack_sub.add_parser("list", help="list parts in a pack")
    p.add_argument("directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "lint":
            return _lint(args)
        if args.command == "pack":
            return _pack(args)

        if args.command == "introspect":
            print(json.dumps(introspect_circuit(args.circuit, timeout=args.timeout), indent=2))
            return 0

        if args.command == "netlist":
            payload = export_netlist(args.circuit, args.out, timeout=args.timeout)
            print(json.dumps(payload, indent=2))
            return 0

        if args.command == "simulate":
            result = run_simulation(
                args.circuit, args.duration, args.rate,
                csv=args.csv, only=args.only, timeout=args.timeout,
            )
            summary = {name: {"min": min(v), "max": max(v)} for name, v in result.signals.items() if v}
            print(json.dumps({
                "csv": str(result.csv_path) if result.csv_path else None,
                "samples": len(result),
                "signals": summary,
            }, indent=2))
            return 0
    except (com.MsCtlError, FileNotFoundError, ValueError, KeyError) as exc:
        print(f"msauto: {exc}", file=sys.stderr)
        return 1

    return 2


def _lint(args) -> int:
    if args.netlist == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.netlist)
        if not path.is_file():
            print(f"msauto: no such netlist: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8-sig")
    issues = lint(text)
    if not issues:
        print("no issues found")
        return 0
    print(format_issues(issues))
    errors = sum(1 for i in issues if i.level == "error")
    if errors:
        return 1
    return 1 if args.strict else 0


def _pack(args) -> int:
    if args.pack_command == "validate":
        problems = template_pack.validate_pack(args.directory)
        if not problems:
            print(f"{args.directory}: OK")
            return 0
        print("\n".join(problems))
        return 1

    if args.pack_command == "list":
        parts = template_pack.list_parts(args.directory)
        for kind, info in sorted(parts.items()):
            state = "ok" if info.complete else "INCOMPLETE"
            print(f"{kind:12} {state:10} ports={len(info.ports)}")
        return 0

    if args.pack_command == "build":
        result = template_pack.build_pack(
            args.base, args.part, args.out, overwrite=args.overwrite,
        )
        print(json.dumps(result, indent=2))
        return 0 if not result["problems"] else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
