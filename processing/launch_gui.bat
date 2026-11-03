@echo off
rem Inicia la GUI del procesamiento Red OTUS v2026.1.0.
rem Desarrollo: Cristian C. Acevedo. Supervision: Angelica Diaz Pulido.
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
set "PYTHONW_EXE=%~dp0..\.venv\Scripts\pythonw.exe"

if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
  set "PYTHONW_EXE=pythonw"
)

"%PYTHON_EXE%" --version >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Consulte ..\docs\OPERATION_MANUAL.md.
  pause
  exit /b 1
)

"%PYTHON_EXE%" -c "import PySide6, PIL" >nul 2>nul
if errorlevel 1 (
  echo El entorno no esta preparado. Siga la instalacion reproducible descrita en ..\docs\OPERATION_MANUAL.md.
  pause
  exit /b 1
)

"%PYTHONW_EXE%" --version >nul 2>nul
if errorlevel 1 (
  "%PYTHON_EXE%" "%~dp0run_gui.py"
) else (
  start "" "%PYTHONW_EXE%" "%~dp0run_gui.py"
)
