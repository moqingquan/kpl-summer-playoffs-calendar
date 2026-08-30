@echo off
setlocal
cd /d "%~dp0"
python update_calendar.py --season-id KPL2026S2 --output kpl-summer-playoffs.ics
endlocal

