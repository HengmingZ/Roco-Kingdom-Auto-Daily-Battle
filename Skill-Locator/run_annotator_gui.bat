@echo off
cd /d "%~dp0"
echo Starting Skill-Locator Annotator GUI...
uv run dataset/annotator_gui.py
pause
