#!/usr/bin/env python3
"""
Простой запуск сервера
"""
import sys
from pathlib import Path

# Правильный путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🚀 Запуск Laprascope API...")
print(f"📁 Project root: {project_root}")

try:
    from app.main import app
    import uvicorn
    
    print("✅ Все импорты успешны!")
    print("🌐 Запускаю сервер на http://0.0.0.0:8000")
    print("📖 Документация: http://0.0.0.0:8000/docs")
    print("❤️  Health check: http://0.0.0.0:8000/api/v1/health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
