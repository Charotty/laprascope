#!/usr/bin/env python3
"""
Тестовый скрипт для проверки всех импортов
"""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent  # Переходим на уровень выше к laprascope/
sys.path.insert(0, str(project_root))

print("🔍 Тестирование импортов...")
print(f"Project root: {project_root}")
print(f"Python path: {sys.path[:3]}...")

try:
    # Тестируем основные импорты
    print("\n📦 Тестируем app.main...")
    from app.main import app
    print("✅ app.main импортирован успешно")
    
    print("\n📦 Тестируем app.config...")
    from app.config import API_CONFIG, CORS_ORIGINS
    print("✅ app.config импортирован успешно")
    
    print("\n📦 Тестируем utils...")
    from app.utils.logging_config import setup_logging, get_logger
    from app.utils.errors import handle_exception, APIError
    print("✅ app.utils импортированы успешно")
    
    print("\n📦 Тестируем API модули...")
    from app.api.upload_fixed import router as upload_router
    from app.api.status import router as status_router
    from app.api.download import router as download_router
    from app.api.metadata import router as metadata_router
    print("✅ app.api модули импортированы успешно")
    
    print("\n📦 Тестируем services...")
    from app.services.pipeline import run_pipeline, create_job, get_job_status
    from app.services.segmentation import segment_kidneys
    from app.services.conversion import convert_organ_to_stl
    from app.services.displacement_parser import get_displacement_for_patient
    print("✅ app.services импортированы успешно")
    
    print("\n🎯 Все импорты работают корректно!")
    print(f"📊 Конфигурация: {API_CONFIG.get('host', 'N/A')}:{API_CONFIG.get('port', 'N/A')}")
    print(f"🌐 CORS origins: {len(CORS_ORIGINS)} доменов")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print(f"📍 Модуль: {e.name if hasattr(e, 'name') else 'Unknown'}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Непредвиденная ошибка: {e}")
    sys.exit(1)

print("\n🚀 Готов к запуску сервера!")
