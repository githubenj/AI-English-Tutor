@echo off
chcp 65001 >nul
title AI-English-Tutor
cd /d F:\AI-English-Tutor

echo Activating virtual environment...
call venv\Scripts\activate

echo Starting assistant...
python main.py

echo.
echo Finished. Press any key to exit.
pause >nul
