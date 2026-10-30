@echo off
title Parar Tickets
cd /d "%~dp0"
python\python.exe -X utf8 web\arrancar.py --parar
timeout /t 5 >nul
