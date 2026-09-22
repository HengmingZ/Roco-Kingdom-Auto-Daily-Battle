@echo off
cd /d "%~dp0"
echo Starting Skill-Locator Collector GUI...
uv run dataset/collector_gui.py
pause
