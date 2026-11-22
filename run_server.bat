@echo off
rem JobMatch API server + background workers (local development).
rem Same entry point as the Dockerfile: the "src.server:app" module, run from the project root
rem (so .env, data\ and logs\ are found). Uses the project's .venv when it exists,
rem instead of whatever "uvicorn" happens to be first on PATH.
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

"%PY%" -m uvicorn src.server:app --reload --reload-dir src --host 0.0.0.0 --port 8000
