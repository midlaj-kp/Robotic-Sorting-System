@echo off
REM Real Camera Startup Script for Convoyer Backend
REM This script automatically finds and uses the real camera

echo ===============================================
echo    CONVOYER - REAL CAMERA MODE
echo ===============================================
echo.

REM Disable mock mode
set MOCK_HARDWARE=false

REM Check if camera index is already set
if not "%CAMERA_INDEX%"=="" (
    echo Using camera index: %CAMERA_INDEX%
    python run.py
    exit /b 0
)

REM Try to find camera automatically
echo Detecting camera...
python find_camera.py
echo.

REM Get camera index from user or use default
set /p CAMERA_INDEX=Enter camera index to use (default 0): 
if "%CAMERA_INDEX%"=="" set CAMERA_INDEX=0

echo.
echo Starting backend with camera index %CAMERA_INDEX%...
set CAMERA_INDEX=%CAMERA_INDEX%
python run.py
