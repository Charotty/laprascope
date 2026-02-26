#!/usr/bin/env python3
"""
Тест импортов без metadata
"""
import sys
from pathlib import Path

# Правильный путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Тест импортов (без metadata)...")
print(f"Project root: {project_root}")

try:
    print("📦 Импортируем app.config...")
    from app.config import API_CONFIG, CORS_ORIGINS, DATA_DIR, JOBS_DIR, ML_CONFIG, BASE_DIR
    print("✅ app.config - OK")
    
    print("📦 Импортируем utils...")
    from app.utils.logging_config import setup_logging, get_logger
    from app.utils.errors import APIError, handle_exception
    print("✅ app.utils - OK")
    
    print("📦 Импортируем services...")
    from app.services.pipeline import run_pipeline, create_job, get_job_status
    from app.services.segmentation import segment_kidneys, SegmentationError
    from app.services.conversion import convert_organ_to_stl, ConversionError
    from app.services.displacement_parser import get_displacement_for_patient
    print("✅ app.services - OK")
    
    print("📦 Импортируем API (кроме metadata)...")
    from app.api.upload_fixed import router as upload_router
    from app.api.status import router as status_router
    from app.api.download import router as download_router
    print("✅ app.api (без metadata) - OK")
    
    print("📦 Импортируем main app без metadata...")
    # Временно отключаем metadata router
    import app.main
    # Удаляем metadata router из приложения
    app.main.app.routes = [r for r in app.main.app.routes if 'metadata' not in str(r.path)]
    print("✅ app.main (без metadata) - OK")
    
    print("\n🎉 ОСНОВНЫЕ ИМПОРТЫ РАБОТАЮТ!")
    print(f"🌐 API Host: {API_CONFIG.get('host', 'localhost')}")
    print(f"🔌 API Port: {API_CONFIG.get('port', 8000)}")
    print(f"📁 Data Dir: {DATA_DIR}")
    print(f"📁 Jobs Dir: {JOBS_DIR}")
    print(f"🤖 ML Device: {ML_CONFIG.get('device', 'cpu')}")
    
    print("\n🚀 Запускаю сервер без metadata endpoint...")
    import uvicorn
    uvicorn.run(app.main.app, host="0.0.0.0", port=8000)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
