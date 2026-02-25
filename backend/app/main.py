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

from .config import API_CONFIG
from .api.upload import router as upload_router
from .api.status import router as status_router
from .api.download import router as download_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

# Создаем директорию для логов
os.makedirs('logs', exist_ok=True)

logger = logging.getLogger(__name__)

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
    allow_origins=["*"],  # В продакшене ограничить конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(status_router, prefix="/api/v1", tags=["status"])
app.include_router(download_router, prefix="/api/v1", tags=["download"])

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик общих исключений"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "internal_error",
                "details": str(exc) if API_CONFIG.get("debug") else None
            }
        }
    )

@app.exception_handler(MemoryError)
async def memory_error_handler(request: Request, exc: MemoryError):
    """Обработчик ошибок памяти (CUDA OOM)"""
    logger.error(f"Memory error: {str(exc)}")
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": 503,
                "message": "Service unavailable due to memory constraints. Please try with a smaller file or try again later.",
                "type": "memory_error"
            }
        }
    )

@app.exception_handler(OSError)
async def os_error_handler(request: Request, exc: OSError):
    """Обработчик ошибок ОС (включая проблемы с DICOM файлами)"""
    logger.error(f"OS error: {str(exc)}")
    
    # Определяем тип ошибки
    if "No such file" in str(exc) or "not found" in str(exc):
        error_type = "file_not_found"
        message = "File not found or corrupted"
    elif "Permission denied" in str(exc):
        error_type = "permission_error"
        message = "Permission denied"
    elif "Invalid DICOM" in str(exc) or "corrupted" in str(exc):
        error_type = "invalid_dicom"
        message = "Invalid or corrupted DICOM file"
    else:
        error_type = "os_error"
        message = "System error occurred"
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": 400,
                "message": message,
                "type": error_type,
                "details": str(exc) if API_CONFIG.get("debug") else None
            }
        }
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
    from .config import DATA_DIR, UPLOADS_DIR, OUTPUT_DIR, JOBS_DIR
    
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
