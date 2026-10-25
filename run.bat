@echo off
title Bangla Proofreader
echo Starting Bangla Proofreader...
python -m app.main
if %errorlevel% neq 0 (
    pause
)
