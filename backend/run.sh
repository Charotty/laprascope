#!/bin/bash

# AR Laparoscopy Backend Startup Script

echo "🚀 Starting AR Laparoscopy Backend..."

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Проверяем виртуальное окружение
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Активируем виртуальное окружение
echo "🔧 Activating virtual environment..."
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

# Устанавливаем зависимости
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Создаем необходимые директории
echo "📁 Creating directories..."
mkdir -p data/uploads data/output data/jobs logs

# Запускаем приложение
echo "🌐 Starting FastAPI application..."
cd app
export PYTHONPATH=..
python main.py
