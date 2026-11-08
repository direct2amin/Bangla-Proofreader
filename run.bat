@echo off
title Bangla Proofreader
echo Starting Bangla Proofreader...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m app.main
) else (
    python -m app.main
)
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error. If running for the first time,
    echo please install dependencies using: pip install -r requirements.txt
    echo.
    pause
)
