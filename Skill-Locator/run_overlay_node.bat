@echo off
cd /d "%~dp0"
:: Check for Administrator privileges to bypass Windows UIPI
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges to send clicks to game...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && uv run inference/screen_overlay_node.py' -Verb RunAs"
    exit /b
)
echo Starting Skill-Locator Screen Overlay Node (Administrator Mode)...
uv run inference/screen_overlay_node.py
pause
