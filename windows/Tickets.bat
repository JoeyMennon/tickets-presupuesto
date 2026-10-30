@echo off
title Tickets presupuesto
cd /d "%~dp0"
python\python.exe -X utf8 web\arrancar.py
if errorlevel 1 pause
