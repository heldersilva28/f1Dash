@echo off
cd /d "%~dp0"
title F1 Dash
call :python || exit /b
%PY% f1dash.py
pause
exit /b

:python
rem O lancador "py" vem sempre com o instalador do python.org, mesmo sem "Add Python to PATH".
rem O "python" da Microsoft Store pode so abrir a loja, por isso confirmo que o Python corre mesmo.
set "PY="
py -3 -c "import sys" >NUL 2>NUL && set "PY=py -3"
if not defined PY python -c "import sys" >NUL 2>NUL && set "PY=python"
if defined PY exit /b 0
echo Nao encontrei o Python.
echo Instala o Python 3.10 ou mais recente em https://www.python.org/downloads/ e volta a abrir este ficheiro.
pause
exit /b 1
