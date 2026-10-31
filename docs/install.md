# Installation

## What you need

| Requirement | Notes |
|---|---|
| Windows 10/11 (x64) | Multisim's COM server is 32-bit, but it runs fine on x64 Windows. |
| NI Multisim 14.x, licensed | Tested with Circuit Design Suite 14.3. |
| .NET Framework 4 | The compiler ships with Windows: `C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe`. |
| Python 3.9+ | msauto itself uses only the standard library. |

## 1. Build `msctl`

```bat
cd csharp
build.cmd
```

The script:

1. compiles `TlbGen.exe` from `TlbGen/TlbGen.cs`;
2. locates `MSInterface.dll` in your Multisim installation and generates
   `bin/Interop.MSInterface.dll` from its type library **on your machine** —
   no NI binary is stored in this repository;
3. compiles the 32-bit `bin/msctl.exe`.

Set `MULTISIM_DIR` if the auto-detection misses your install:

```bat
set MULTISIM_DIR=D:\NI\Circuit Design Suite 14.2
csharp\build.cmd
```

Git Bash / MSYS2 users can run `csharp/build.sh` instead.

## 2. Install the Python package

```bat
pip install -e python
```

## 3. Point msauto at `msctl`

In order of preference:

1. `set MSAUTO_MSCTL=C:\path\to\msctl.exe`
2. put `csharp\bin` on `PATH`
3. keep the repository layout — msauto finds `csharp/bin/msctl.exe` next to the
   `python/` directory automatically.

## 4. Smoke test

```bat
msctl introspect C:\circuits\anything.ms14
python -c "import msauto; print(msauto.__version__)"
```

`msctl` starts a hidden Multisim instance, so the first call takes a few
seconds while the application boots.

## Optional: template packs

Building *new* schematics needs component templates extracted from your own
Multisim installation. See [template-packs.md](template-packs.md).
