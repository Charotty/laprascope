@echo off
REM AR Laparoscopy Backend Startup Script for Windows

echo 🚀 Starting AR Laparoscopy Backend...

REM Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Проверяем виртуальное окружение
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Активируем виртуальное окружение
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Устанавливаем зависимости
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Создаем необходимые директории
echo 📁 Creating directories...
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "data\output" mkdir data\output
if not exist "data\jobs" mkdir data\jobs
if not exist "logs" mkdir logs

REM Запускаем приложение
echo 🌐 Starting FastAPI application...
cd app
python main.py

pause
