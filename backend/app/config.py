"""
Конфигурация AR Laparoscopy Project
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
JOBS_DIR = DATA_DIR / "jobs"

# Создаем директории если не существуют
for dir_path in [DATA_DIR, UPLOADS_DIR, OUTPUT_DIR, JOBS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ML конфигурация
ML_CONFIG = {
    "roi_subset": ["kidney_left", "kidney_right"],
    "fast_mode": True,
    "device": "cpu",  # Можно изменить на "cuda" если доступна GPU
    "target_faces": 50000,  # Для STL конвертации
}

# API конфигурация
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True,
    "reload": True,
}

# CORS конфигурация
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    CORS_ORIGINS = [
        "https://your-production-domain.com",
        "https://www.your-production-domain.com"
    ]
else:
    # Для разработки разрешаем локальные адреса
    CORS_ORIGINS = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",   # Simple HTML server (legacy)
        "http://127.0.0.1:8080"
    ]

# Поддерживаемые форматы файлов
SUPPORTED_INPUT_FORMATS = [".nii", ".nii.gz", ".dcm"]
SUPPORTED_OUTPUT_FORMATS = [".nii.gz", ".stl"]

# Максимальный размер файла для загрузки (100MB)
MAX_UPLOAD_SIZE = 100 * 1024 * 1024

# Время ожидания обработки (в секундах)
PROCESSING_TIMEOUT = 300  # 5 минут
