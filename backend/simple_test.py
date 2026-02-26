#!/usr/bin/env python3
"""
Простой тест импортов
"""
import sys
from pathlib import Path

# Правильный путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Тест импортов...")
print(f"Project root: {project_root}")

try:
    print("📦 Импортируем app.main...")
    from app.main import app
    print("✅ Успешно!")
    
    print("📦 Импортируем app.config...")
    from app.config import API_CONFIG
    print("✅ Успешно!")
    
    print("📦 Импортируем utils...")
    from app.utils.logging_config import setup_logging
    from app.utils.errors import APIError
    print("✅ Успешно!")
    
    print("📦 Импортируем services...")
    from app.services.pipeline import run_pipeline
    from app.services.segmentation import segment_kidneys
    print("✅ Успешно!")
    
    print("🎉 Все импорты работают!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
