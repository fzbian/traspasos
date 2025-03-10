@echo off
echo ===================================================
echo Windows Setup Script for Flet Application
echo ===================================================

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python is installed. Proceeding with setup...

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        echo Please make sure you have the venv module installed.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing required packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements.
    echo Please check if requirements.txt exists and is valid.
    pause
    exit /b 1
)

echo ===================================================
echo Setup completed successfully!
echo ===================================================
echo.
echo To run the application:
echo 1. Activate the virtual environment (if not already activated):
echo    call venv\Scripts\activate.bat
echo.
echo 2. Run the main application:
echo    python main.py
echo.
echo To deactivate the virtual environment when done:
echo    deactivate
echo ===================================================

pause

