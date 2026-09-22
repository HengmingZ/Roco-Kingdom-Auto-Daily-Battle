@echo off
cd /d "%~dp0"
echo Starting Skill-Locator Coordinate Tracker Node...
uv run inference/coordinate_tracker_node.py
pause
