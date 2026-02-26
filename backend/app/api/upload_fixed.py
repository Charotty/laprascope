"""
Улучшенный API endpoint для загрузки DICOM файлов с правильной структурой
"""
import os
import sys
import uuid
import zipfile
import logging
import pydicom
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

from services.pipeline import run_pipeline, create_job, PipelineError
from config import UPLOADS_DIR, JOBS_DIR, MAX_UPLOAD_SIZE

logger = logging.getLogger(__name__)
router = APIRouter()

def validate_dicom_file(file_path: Path) -> bool:
    """Проверяет что файл является DICOM"""
    try:
        ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        return hasattr(ds, 'PatientName') and hasattr(ds, 'Modality')
    except Exception as e:
        logger.warning(f"Invalid DICOM file {file_path}: {e}")
        return False

def find_dicom_files(dicom_dir: Path) -> List[Path]:
    """Находит все DICOM файлы в директории рекурсивно"""
    dicom_files = []
    
    # Рекурсивный поиск всех файлов
    for file_path in dicom_dir.rglob("*"):
        if file_path.is_file():
            # Пропускаем служебные файлы
            if file_path.name in ['DICOMDIR', 'Autorun.inf', 'amImageViewer.exe']:
                continue
                
            # Проверяем расширение или бинарный формат
            if (file_path.suffix.lower() in ['.dcm', '.dicom', '.dic'] or 
                not file_path.suffix):  # Файлы без расширения
                
                # Дополнительная валидация через pydicom
                if validate_dicom_file(file_path):
                    dicom_files.append(file_path)
    
    return dicom_files

def organize_dicom_files(dicom_files: List[Path], target_dir: Path) -> bool:
    """Организует DICOM файлы в плоскую структуру для TotalSegmentator"""
    try:
        target_dir.mkdir(exist_ok=True)
        
        # Копируем все DICOM файлы в одну директорию
        for i, dicom_file in enumerate(dicom_files):
            # Генерируем новое имя с расширением .dcm
            new_name = f"slice_{i:04d}.dcm"
            target_path = target_dir / new_name
            
            # Копируем файл
            import shutil
            shutil.copy2(dicom_file, target_path)
            
        logger.info(f"Copied {len(dicom_files)} DICOM files to {target_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error organizing DICOM files: {e}")
        return False

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_fio: str = None
) -> Dict:
    """
    Загружает ZIP архив с DICOM файлами и запускает обработку
    
    Args:
        background_tasks: FastAPI background tasks
        file: загруженный файл (ZIP с DICOM)
        patient_fio: ФИО пациента для связи с CSV данными смещения
        
    Returns:
        Dict: информация о созданной задаче
    """
    logger.info(f"Received upload request: {file.filename}")
    
    try:
        # Проверяем размер файла
        if file.size and file.size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )
        
        # Проверяем формат файла
        if not file.filename or not file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail="Only ZIP files are supported"
            )
        
        # Генерируем уникальный job_id
        job_id = uuid.uuid4().hex
        logger.info(f"Generated job_id: {job_id}")
        
        # Создаем директории для задачи
        job_dir = JOBS_DIR / job_id
        dicom_dir = job_dir / "dicom"
        organized_dir = job_dir / "dicom_organized"
        
        for dir_path in [job_dir, dicom_dir, organized_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Сохраняем загруженный файл
        upload_path = UPLOADS_DIR / f"{job_id}_{file.filename}"
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        
        logger.info(f"Saving uploaded file to {upload_path}")
        
        # Читаем и сохраняем файл
        content = await file.read()
        with open(upload_path, 'wb') as f:
            f.write(content)
        
        # Распаковываем ZIP архив
        logger.info(f"Extracting ZIP to {dicom_dir}")
        try:
            with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                zip_ref.extractall(dicom_dir)
        except zipfile.BadZipFile:
            # Удаляем файлы если ZIP поврежден
            upload_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="Invalid ZIP file"
            )
        
        # Находим DICOM файлы в распакованной структуре
        dicom_files = find_dicom_files(dicom_dir)
        
        if not dicom_files:
            # Удаляем распакованные файлы
            import shutil
            shutil.rmtree(dicom_dir, ignore_errors=True)
            upload_path.unlink(missing_ok=True)
            
            raise HTTPException(
                status_code=400,
                detail="No valid DICOM files found in ZIP archive. Expected structure: Patient/Date/Series/DICOM files"
            )
        
        # Организуем файлы в плоскую структуру для TotalSegmentator
        if not organize_dicom_files(dicom_files, organized_dir):
            raise HTTPException(
                status_code=500,
                detail="Failed to organize DICOM files"
            )
        
        # Создаем status файл
        status_data = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "patient_fio": patient_fio,
            "dicom_count": len(dicom_files),
            "original_structure": str(dicom_dir),
            "organized_structure": str(organized_dir)
        }
        
        status_file = job_dir / "status.json"
        import json
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        # Запускаем pipeline в фоне
        background_tasks.add_task(run_pipeline, job_id, str(organized_dir))
        
        # Удаляем загруженный ZIP файл
        upload_path.unlink(missing_ok=True)
        
        logger.info(f"Successfully processed upload for job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Successfully uploaded {len(dicom_files)} DICOM files",
            "dicom_count": len(dicom_files),
            "patient_fio": patient_fio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/upload-info")
def get_upload_info():
    """Информация о поддерживаемых форматах загрузки"""
    return {
        "supported_formats": ["ZIP"],
        "expected_structure": {
            "description": "ZIP должен содержать DICOM файлы в любой вложенности",
            "examples": [
                "PatientName/StudyDate/Series/00000001, 00000002, ...",
                "StudyDate/Series/00000001, 00000002, ...",
                "Series/00000001, 00000002, ...",
                "00000001, 00000002, ..."
            ]
        },
        "file_validation": {
            "checks": [
                "DICOM header validation",
                "PatientName presence",
                "Modality presence",
                "File format verification"
            ]
        },
        "max_file_size": f"{MAX_UPLOAD_SIZE // (1024*1024)}MB"
    }
