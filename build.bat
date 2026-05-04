@echo off
REM ─────────────────────────────────────────────────────────────────────
REM  build.bat  —  Build ExpenseTracker.exe with PyInstaller
REM  Run from the project root:  build.bat
REM ─────────────────────────────────────────────────────────────────────

echo.
echo ==========================================================
echo  Expense Tracker  —  PyInstaller build
echo ==========================================================
echo.

REM 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

REM 2. Install / upgrade all dependencies
echo [1/3]  Installing dependencies...
pip install --upgrade -r requirements.txt
if errorlevel 1 ( echo ERROR: pip install failed. & pause & exit /b 1 )

REM 3. Clean previous build artefacts
echo [2/3]  Cleaning previous build...
if exist build  rd /s /q build
if exist dist   rd /s /q dist

REM 4. Run PyInstaller
echo [3/3]  Building executable...
pyinstaller expense_tracker.spec
if errorlevel 1 ( echo ERROR: PyInstaller failed. & pause & exit /b 1 )

echo.
echo ==========================================================
echo  Build complete!
echo  Your app is in:  dist\ExpenseTracker\ExpenseTracker.exe
echo  ZIP that folder and share it with friends.
echo ==========================================================
echo.
pause
