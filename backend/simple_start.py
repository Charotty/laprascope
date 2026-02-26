#!/usr/bin/env python3
"""
Максимально простой запуск сервера
"""
import sys
from pathlib import Path

# Правильный путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🚀 Запуск Laprascope API...")

try:
    # Импортируем и запускаем
    from app.main import app
    import uvicorn
    
    print("✅ Импорты успешны!")
    print("🌐 Сервер запускается на http://0.0.0.0:8000")
    print("📖 Документация: http://0.0.0.0:8000/docs")
    
    # Запускаем с базовыми настройками
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
