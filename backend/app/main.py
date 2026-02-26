"""
Main FastAPI application for AR Laparoscopy Project
"""
import os
import sys
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".venv" / "Lib" / "site-packages"))

# Устанавливаем PYTHONPATH для корректных относительных импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import API_CONFIG, CORS_ORIGINS
from api.upload_fixed import router as upload_router
from api.status import router as status_router
from api.download import router as download_router
from api.metadata import router as metadata_router

from utils.logging_config import setup_logging, get_logger
from utils.errors import handle_exception, APIError

# Настраиваем улучшенное логирование
logger = setup_logging(
    log_level=API_CONFIG.get("log_level", "INFO"),
    log_dir="logs",
    enable_console=True,
    enable_file=True
)

# Создаем FastAPI приложение
app = FastAPI(
    title="AR Laparoscopy API",
    description="API for DICOM segmentation and STL generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(status_router, prefix="/api/v1", tags=["status"])
app.include_router(download_router, prefix="/api/v1", tags=["download"])
app.include_router(metadata_router, prefix="/api/v1", tags=["metadata"])

# Exception handlers с унифицированной обработкой
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Обработчик стандартизированных API ошибок"""
    exc.log(logger, f"API Error in {request.url.path}")
    
    # Определяем HTTP статус на основе типа ошибки
    status_codes = {
        "validation_error": 400,
        "authentication_error": 401,
        "authorization_error": 403,
        "rate_limit_error": 429,
        "timeout_error": 408,
        "network_error": 503,
        "processing_error": 500,
        "file_system_error": 500,
        "memory_error": 503,
        "unknown_error": 500
    }
    
    status_code = status_codes.get(exc.error_type.value, 500)
    
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих исключений"""
    api_error = handle_exception(
        logger=logger,
        exception=exc,
        context=f"Request: {request.method} {request.url.path}",
        default_message="Internal server error"
    )
    
    # Определяем статус на основе типа ошибки
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        status_code = 404
    elif isinstance(exc, ValueError):
        status_code = 400
    else:
        status_code = 500
    
    return JSONResponse(
        status_code=status_code,
        content=api_error.to_dict()
    )


# Root endpoint
@app.get("/")
async def root():
    """Корневой endpoint с информацией об API"""
    return {
        "name": "AR Laparoscopy API",
        "version": "1.0.0",
        "description": "API for DICOM segmentation and STL generation",
        "docs": "/docs",
        "endpoints": {
            "upload": "/api/v1/upload",
            "upload_nifti": "/api/v1/upload-nifti",
            "status": "/api/v1/status/{job_id}",
            "jobs": "/api/v1/jobs",
            "download_stl": "/api/v1/stl/{job_id}/{organ}",
            "download_nifti": "/api/v1/nifti/{job_id}/{organ}",
            "download_all": "/api/v1/download/{job_id}/all",
            "files": "/api/v1/files/{job_id}",
            "metadata": "/api/v1/metadata/{job_id}",
            "link_patient": "/api/v1/metadata/{job_id}/link-patient",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats"
        },
        "supported_organs": ["kidney_left", "kidney_right"],
        "supported_formats": {
            "input": [".nii", ".nii.gz", ".zip (DICOM)"],
            "output": [".nii.gz", ".stl"]
        }
    }

@app.get("/api/v1/info")
async def api_info():
    """Информация о конфигурации API"""
    return {
        "api_config": API_CONFIG,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "working_directory": str(Path.cwd()),
        "log_file": "logs/app.log"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    logger.info("🚀 AR Laparoscopy API starting up...")
    
    # Проверяем GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            gpu_memory_gb = gpu_memory / (1024**3)
            logger.info(f"🎮 GPU detected: {gpu_name}")
            logger.info(f"💾 GPU Memory: {gpu_memory_gb:.1f} GB")
        else:
            logger.warning("⚠️ No GPU detected. Using CPU for processing (slower)")
    except Exception as e:
        logger.warning(f"Failed to check GPU: {e}")
    
    # Проверяем необходимые директории
    from config import DATA_DIR, UPLOADS_DIR, OUTPUT_DIR, JOBS_DIR
    
    for dir_name, dir_path in [
        ("data", DATA_DIR),
        ("uploads", UPLOADS_DIR),
        ("output", OUTPUT_DIR),
        ("jobs", JOBS_DIR)
    ]:
        if not dir_path.exists():
            logger.warning(f"Directory {dir_name} not found at {dir_path}")
            dir_path.mkdir(exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
        else:
            logger.info(f"Directory {dir_name} exists: {dir_path}")
    
    logger.info("✅ AR Laparoscopy API ready!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения"""
    logger.info("🛑 AR Laparoscopy API shutting down...")

if __name__ == "__main__":
    # Запуск приложения
    logger.info("Starting AR Laparoscopy API...")
    
    uvicorn.run(
        "main:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["reload"],
        log_level="info"
    )
