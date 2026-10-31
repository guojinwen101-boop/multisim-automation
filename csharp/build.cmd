@echo off
rem Build the 32-bit COM interop assembly and msctl.exe.
rem Requires the .NET Framework 4 compiler that ships with Windows and a
rem licensed NI Multisim 14.x installation (only its type library is read).
setlocal

set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
if not exist "%CSC%" (
  echo ERROR: .NET Framework 4 csc.exe not found at %CSC%
  exit /b 1
)

if not defined MULTISIM_DIR set "MULTISIM_DIR=C:\Program Files (x86)\National Instruments\Circuit Design Suite 14.3"
if not exist "%MULTISIM_DIR%\MSInterface.dll" goto find_multisim
goto have_multisim

:find_multisim
for /d %%D in ("C:\Program Files (x86)\National Instruments\Circuit Design Suite*") do set "MULTISIM_DIR=%%D"
if not exist "%MULTISIM_DIR%\MSInterface.dll" (
  echo ERROR: MSInterface.dll not found. Set MULTISIM_DIR to your Multisim install.
  exit /b 1
)

:have_multisim
echo Using Multisim at "%MULTISIM_DIR%"
if not exist bin mkdir bin
cd /d "%~dp0"

echo [1/3] TlbGen.exe
"%CSC%" /nologo /platform:x86 /out:bin\TlbGen.exe TlbGen\TlbGen.cs || exit /b 1

echo [2/3] Interop.MSInterface.dll from "%MULTISIM_DIR%\MSInterface.dll"
bin\TlbGen.exe "%MULTISIM_DIR%\MSInterface.dll" bin\Interop.MSInterface.dll MultisimInterop || exit /b 1

echo [3/3] msctl.exe
"%CSC%" /nologo /platform:x86 /r:bin\Interop.MSInterface.dll /out:bin\msctl.exe MsCtl\Program.cs || exit /b 1

echo.
echo Done: %~dp0bin\msctl.exe
echo Add this directory to PATH or set MSAUTO_MSCTL=%~dp0bin\msctl.exe
exit /b 0
