@echo off
chcp 65001 >nul
cd /d "%~dp0"
python FACE_ID\deneme.py --demo
if errorlevel 1 pause
