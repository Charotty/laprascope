#!/bin/bash
# Правильный запускной скрипт для Laprascope API

# Переходим в директорию проекта
cd /root/laprascope

# Активируем виртуальное окружение
source backend/.venv/bin/activate

# Устанавливаем PYTHONPATH
export PYTHONPATH=/root/laprascope:$PYTHONPATH

# Переходим в бэкенд
cd backend

echo "🚀 Запуск Laprascope API..."
echo "📁 Project root: /root/laprascope"
echo "🐍 Python path: $PYTHONPATH"
echo "📖 Docs: http://0.0.0.0:8000/docs"
echo "❤️  Health: http://0.0.0.0:8000/api/v1/health"

# Запускаем сервер
python -m app.main --host 0.0.0.0 --port 8000
