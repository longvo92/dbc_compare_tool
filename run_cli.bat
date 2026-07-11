@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo venv missing. run: python -m venv .venv
    exit /b 1
)
.venv\Scripts\python.exe -m dbc_compare_tool.cli %*
