@echo off
cd /d "%~dp0"
title F1 Dash
where python >NUL 2>NUL || (echo Nao encontrei o Python. Instala em https://www.python.org/downloads/ e marca "Add Python to PATH". & pause & exit /b)
python f1dash.py
pause
