#!/usr/bin/env bash
# Same job as build.cmd, for Git Bash / MSYS2 users.
set -euo pipefail
cd "$(dirname "$0")"

CSC="${CSC:-/c/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe}"
MULTISIM_DIR="${MULTISIM_DIR:-/c/Program Files (x86)/National Instruments/Circuit Design Suite 14.3}"

if [ ! -f "$MULTISIM_DIR/MSInterface.dll" ]; then
  for d in "/c/Program Files (x86)/National Instruments/"Circuit\ Design\ Suite*; do
    [ -f "$d/MSInterface.dll" ] && MULTISIM_DIR="$d" && break
  done
fi
if [ ! -f "$MULTISIM_DIR/MSInterface.dll" ]; then
  echo "ERROR: MSInterface.dll not found. Set MULTISIM_DIR." >&2
  exit 1
fi

mkdir -p bin
export MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV=1

echo "[1/3] TlbGen.exe"
"$CSC" /nologo /platform:x86 /out:bin/TlbGen.exe TlbGen/TlbGen.cs

echo "[2/3] Interop.MSInterface.dll from $MULTISIM_DIR/MSInterface.dll"
./bin/TlbGen.exe "$MULTISIM_DIR/MSInterface.dll" bin/Interop.MSInterface.dll MultisimInterop

echo "[3/3] msctl.exe"
"$CSC" /nologo /platform:x86 /r:bin/Interop.MSInterface.dll /out:bin/msctl.exe MsCtl/Program.cs

echo "Done: $(pwd)/bin/msctl.exe"
