@echo off
echo Starting application...

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the application
python main.py

REM If the application exits, keep the window open until the user presses a key
echo.
echo Application has stopped. Press any key to close this window...
pause > nul

