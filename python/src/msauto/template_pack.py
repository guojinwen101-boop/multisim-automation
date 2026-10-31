"""Work with local component template packs.

A template pack is a directory of XML fragments that tell the schematic
builder how to instantiate a component's Multisim object. For a part called
``d85`` the pack contains::

    d85_element.xml        the component template (SPICE card, attributes)
    sym_d85.xml            the symbol drawing
    d85_port1.xml ..       one file per pin/port

Packs are extracted from **your own licensed** Multisim installation. They are
never redistributable; keep them out of git (see ``.gitignore``).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

ELEMENT_SUFFIX = "_element.xml"
SYMBOL_PREFIX = "sym_"
PORT_MARKER = "_port"


@dataclass
class PartInfo:
    kind: str
    element: Path
    symbol: Path | None
    ports: list[Path] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.symbol is not None and bool(self.ports)


def list_parts(root: str | Path) -> dict[str, PartInfo]:
    """Map kind -> files found in a template pack directory."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"template pack not found: {root}")
    parts: dict[str, PartInfo] = {}
    for element in sorted(root.glob(f"*{ELEMENT_SUFFIX}")):
        kind = element.name[: -len(ELEMENT_SUFFIX)]
        symbol = root / f"{SYMBOL_PREFIX}{kind}.xml"
        ports = sorted(root.glob(f"{kind}{PORT_MARKER}*.xml"))
        parts[kind] = PartInfo(
            kind=kind,
            element=element,
            symbol=symbol if symbol.is_file() else None,
            ports=ports,
        )
    return parts


def validate_pack(root: str | Path) -> list[str]:
    """Return a list of human-readable problems (empty means the pack is usable)."""
    root = Path(root)
    problems: list[str] = []
    if not root.is_dir():
        return [f"{root} is not a directory"]

    parts = list_parts(root)
    if not parts:
        return [f"{root} contains no *_element.xml templates"]

    for kind, info in parts.items():
        if info.symbol is None:
            problems.append(f"{kind}: missing symbol file {SYMBOL_PREFIX}{kind}.xml")
        if not info.ports:
            problems.append(f"{kind}: no port files ({kind}{PORT_MARKER}N.xml)")

    symbols = {p.name[len(SYMBOL_PREFIX):-4] for p in root.glob(f"{SYMBOL_PREFIX}*.xml")}
    for orphan in sorted(symbols - set(parts)):
        problems.append(f"{orphan}: symbol without element template")

    return problems


def build_pack(base: str | Path, part_dirs: list[str | Path], out: str | Path,
               *, overwrite: bool = False) -> dict:
    """Copy ``base`` to ``out`` and overlay every ``*.xml`` from ``part_dirs``.

    ``base`` is normally the generic pack produced by the local extraction tool;
    ``part_dirs`` hold additional (extracted or synthesized) parts.
    """
    base, out = Path(base), Path(out)
    if not base.is_dir():
        raise NotADirectoryError(f"base pack not found: {base}")
    if out.exists():
        if not overwrite:
            raise FileExistsError(f"{out} already exists (pass overwrite=True to replace it)")
        shutil.rmtree(out)

    shutil.copytree(base, out)

    copied: list[str] = []
    for directory in map(Path, part_dirs):
        if not directory.is_dir():
            raise NotADirectoryError(f"part directory not found: {directory}")
        for xml in sorted(directory.glob("*.xml")):
            shutil.copy2(xml, out / xml.name)
            copied.append(xml.name)

    parts = list_parts(out)
    return {
        "out": str(out),
        "files": len(list(out.glob("*.xml"))),
        "overlaid": copied,
        "parts": sorted(parts),
        "problems": validate_pack(out),
    }
