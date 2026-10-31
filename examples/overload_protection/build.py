"""Build the overload-protection schematic from design.net.

Prerequisites
-------------
* ``multisim-mcp`` installed (or MULTISIM_MCP_PATH pointing at its checkout).
* A local template pack containing the parts used by design.net:
  d85, d48, d161, d157, n00, n04, seg, q2222, diode.
  Point MULTISIM_MCP_TEMPLATE_DIR at it (see docs/template-packs.md).

Run
---
    python build.py --out out/overload_v1.ms14
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PORTS = {
    "D161": tuple(f"d161_port{i}.xml" for i in range(1, 17)),
    "D157": tuple(f"d157_port{i}.xml" for i in range(1, 17)),
    "D85": (
        "d85_port1.xml", "d85_port2.xml", "d85_port3.xml", "d85_port4.xml",
        "d85_port5.xml", "d85_port6.xml", "d85_port7.xml", "d85_port8.xml",
        "d85_port10.xml", "d85_port11.xml", "d85_port9.xml",
        "d85_port14.xml", "d85_port15.xml", "d85_port13.xml",
        "d85_port12.xml", "d85_port16.xml",
    ),
    "D48": (
        "d48_port15.xml", "d48_port16.xml", "d48_port4.xml", "d48_port3.xml",
        "d48_port2.xml", "d48_port1.xml", "d48_port14.xml",
        "d48_port6.xml", "d48_port7.xml", "d48_port8.xml", "d48_port9.xml",
        "d48_port10.xml", "d48_port11.xml", "d48_port12.xml",
        "d48_port5.xml", "d48_port13.xml",
    ),
    "SEG": (
        "seg_port1.xml", "seg_port2.xml", "seg_port3.xml", "seg_port5.xml",
        "seg_port6.xml", "seg_port7.xml", "seg_port8.xml", "seg_port9.xml",
        "seg_port4.xml",
    ),
    "N00": tuple(f"n00_port{i}.xml" for i in range(1, 6)),
    "N04": tuple(f"n04_port{i}.xml" for i in range(1, 5)),
    "QNPN": ("q2222_port2.xml", "q2222_port1.xml", "q2222_port3.xml"),
    "D": ("diode_port1.xml", "diode_port2.xml"),
}
ELEMENTS = {
    "D161": "d161", "D157": "d157", "D85": "d85", "D48": "d48", "SEG": "seg",
    "N00": "n00", "N04": "n04", "QNPN": "q2222", "D": "diode",
}
SYMBOLS = dict(ELEMENTS)
ALIASES = {
    "74LS161": "D161", "74LS157": "D157", "74LS85": "D85", "74LS48": "D48",
    "74LS00": "N00", "74LS04": "N04", "SEG": "SEG",
}

PROBES = ["q0", "q1", "q2", "ge1", "ge2",
          "sa1", "sb1", "sc1", "sd1", "se1", "sf1", "sg1",
          "sa2", "sg2", "l1a", "z2a", "coil1", "coil2"]

POSITIONS = {
    "VDD": [60, 1250], "VIH": [60, 120], "VIL": [60, 300], "VRST": [60, 480],
    "AU12": [300, 120], "AU11": [300, 300], "AU13": [560, 210],
    "AU5": [60, 700], "AU6": [60, 880], "AU7": [60, 1060],
    "AU14": [300, 700], "AU15": [560, 700], "AU16": [300, 880], "AU17": [560, 880],
    "AU18": [820, 700], "AU19": [1080, 700], "AU20": [300, 1060],
    "AU21": [560, 1060], "AU22": [820, 880], "AU23": [820, 1060],
    "AU24": [1080, 1060], "AU8": [1340, 1060],
    "AU1": [1340, 210], "AU2": [1640, 210],
    "AU3": [1980, 120], "AU4": [1980, 420],
    "AU9": [2280, 120], "AU10": [2280, 420],
    "RNU4": [1900, 700], "RGN1": [2500, 120], "RGN2": [2500, 420],
    "AU25": [1300, 1350],
    "AU26": [1560, 1300], "AU27": [1560, 1380], "AU28": [1560, 1460],
    "AU29": [1560, 1540], "AU30": [1560, 1620], "AU31": [1560, 1700],
    "AU32": [1560, 1780],
    "R1A": [1800, 1300], "R1B": [1800, 1380], "R1C": [1800, 1460],
    "R1D": [1800, 1540], "R1E": [1800, 1620], "R1F": [1800, 1700],
    "R1G": [1800, 1780], "RDP1": [1800, 1900],
    "AD1": [2020, 1500],
    "AU33": [1300, 2100],
    "AU34": [1560, 2020], "AU35": [1560, 2100], "AU36": [1560, 2180],
    "AU37": [1560, 2260], "AU38": [1560, 2340], "AU39": [1560, 2420],
    "AU40": [1560, 2500],
    "R2A": [1800, 2020], "R2B": [1800, 2100], "R2C": [1800, 2180],
    "R2D": [1800, 2260], "R2E": [1800, 2340], "R2F": [1800, 2420],
    "R2G": [1800, 2500],
    "AD2": [2020, 2150],
    "RB1": [2300, 1350], "Q1": [2450, 1350], "XRK1": [2650, 1350],
    "R1L": [2850, 1350], "D1L": [2980, 1350],
    "RB2": [2300, 1650], "Q2": [2450, 1650], "XRK2": [2650, 1650],
    "R2Z": [2850, 1650], "D2Z": [2980, 1650],
}

SHEET_SIZE = [3300, 2700]


def import_builder():
    try:
        from multisim_mcp import schematic_builder, server
        return schematic_builder, server
    except ImportError:
        pass
    root = os.environ.get("MULTISIM_MCP_PATH")
    if not root:
        raise SystemExit(
            "multisim-mcp is not installed. Install it, or set MULTISIM_MCP_PATH "
            "to the folder that contains mcp_server/."
        )
    sys.path.insert(0, str(Path(root) / "mcp_server"))
    from multisim_mcp import schematic_builder, server
    return schematic_builder, server


def check_templates() -> Path:
    raw = os.environ.get("MULTISIM_MCP_TEMPLATE_DIR")
    if not raw:
        raise SystemExit("MULTISIM_MCP_TEMPLATE_DIR is not set; see docs/template-packs.md")
    pack = Path(raw)
    if not pack.is_dir():
        raise SystemExit(f"MULTISIM_MCP_TEMPLATE_DIR does not exist: {pack}")
    missing = [
        f"{kind}_element.xml"
        for kind in ELEMENTS.values()
        if not (pack / f"{kind}_element.xml").is_file()
    ]
    if missing:
        raise SystemExit(f"template pack is missing: {', '.join(missing)}")
    return pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(HERE / "out" / "overload_v1.ms14"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    check_templates()
    sb, server = import_builder()

    for kind, ports in PORTS.items():
        sb.COMPONENT_DEFINITIONS[kind] = sb.ComponentDefinition(
            kind, f"{ELEMENTS[kind]}_element.xml", f"sym_{SYMBOLS[kind]}.xml",
            ports, 36, 117, 180,
        )
    sb.DIGITAL_MODEL_KINDS.update(ALIASES)

    netlist = (HERE / "design.net").read_text(encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    result = server.create_schematic_from_netlist(
        netlist, str(out),
        probe_nets=PROBES,
        include_experimental_probes=True,
        open_after_build=False,
        component_positions=POSITIONS,
        sheet_size=SHEET_SIZE,
        overwrite=args.overwrite,
        verify=False,
    )
    layout = result.get("layout_validation", {})
    print(f"built {result.get('ms14')}")
    print(f"layout: {layout.get('status')}  crossings/wire: {layout.get('crossings_per_wire')}")
    for warning in result.get("warnings", [])[:10]:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
