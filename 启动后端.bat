@echo off
cd /d "%~dp0"
set AIRPLANE_DB_HOST=127.0.0.1
set AIRPLANE_DB_PORT=3306
set AIRPLANE_DB_USER=root
if "%AIRPLANE_DB_PASSWORD%"=="" (
    echo Please set AIRPLANE_DB_PASSWORD before starting the backend.
    pause
    exit /b 1
)
set AIRPLANE_DB_NAME=airplane_game
python "%~dp0backend\app.py"
pause
