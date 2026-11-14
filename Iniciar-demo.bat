@echo off
cd /d "%~dp0"
title F1 Dash - demonstracao
where python >NUL 2>NUL || (echo Nao encontrei o Python. Instala em https://www.python.org/downloads/ e marca "Add Python to PATH". & pause & exit /b)
echo Escolhe a sessao a simular:
echo   1 - Corrida
echo   2 - Qualificacao
echo   3 - Treinos livres
choice /c 123 /n /m "Opcao: "
if errorlevel 3 (set MODO=treinos) else if errorlevel 2 (set MODO=qualificacao) else (set MODO=corrida)
python f1dash.py --demo %MODO%
pause
