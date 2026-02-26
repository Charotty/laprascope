"""
API endpoint для загрузки файлов
"""
import os
import sys
import uuid
import zipfile
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

from services.pipeline import run_pipeline, create_job, PipelineError
from config import UPLOADS_DIR, JOBS_DIR, MAX_UPLOAD_SIZE

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict:
    """
    Загружает ZIP архив с DICOM файлами и запускает обработку
    
    Args:
        background_tasks: FastAPI background tasks
        file: загруженный файл (ZIP с DICOM)
        
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
        
        for dir_path in [job_dir, dicom_dir]:
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
        
        # Проверяем, что в DICOM директории есть файлы
        dicom_files = list(dicom_dir.rglob("*"))
        if not dicom_files:
            raise HTTPException(
                status_code=400,
                detail="No files found in ZIP archive"
            )
        
        logger.info(f"Extracted {len(dicom_files)} files")
        
        # Создаем status.json
        status_data = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "upload_filename": file.filename,
            "files_count": len(dicom_files)
        }
        
        status_file = job_dir / "status.json"
        import json
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Запускаем pipeline в фоне
        logger.info(f"Starting background pipeline for job {job_id}")
        background_tasks.add_task(run_pipeline_with_input, job_id, str(dicom_dir))
        
        # Удаляем временный ZIP файл
        background_tasks.add_task(cleanup_upload_file, upload_path)
        
        logger.info(f"✅ Upload completed for job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "File uploaded successfully. Processing started.",
            "files_count": len(dicom_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

async def run_pipeline_with_input(job_id: str, input_path: str) -> None:
    """
    Wrapper для запуска pipeline в background task
    
    Args:
        job_id: ID задачи
        input_path: путь к входным данным
    """
    try:
        logger.info(f"Background pipeline started for job {job_id}")
        result = run_pipeline(job_id, input_path)
        logger.info(f"Background pipeline completed for job {job_id}")
    except PipelineError as e:
        logger.error(f"Background pipeline failed for job {job_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in background pipeline for job {job_id}: {e}")

async def cleanup_upload_file(file_path: str) -> None:
    """
    Удаляет временный загруженный файл
    
    Args:
        file_path: путь к файлу для удаления
    """
    try:
        Path(file_path).unlink(missing_ok=True)
        logger.info(f"Cleaned up upload file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup upload file {file_path}: {e}")

@router.post("/upload-nifti")
async def upload_nifti(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> Dict:
    """
    Загружает NIfTI файл и запускает обработку
    
    Args:
        background_tasks: FastAPI background tasks
        file: загруженный NIfTI файл
        
    Returns:
        Dict: информация о созданной задаче
    """
    logger.info(f"Received NIfTI upload request: {file.filename}")
    
    try:
        # Проверяем формат файла
        if not file.filename or not (file.filename.lower().endswith('.nii') or file.filename.lower().endswith('.nii.gz')):
            raise HTTPException(
                status_code=400,
                detail="Only NIfTI files (.nii, .nii.gz) are supported"
            )
        
        # Генерируем уникальный job_id
        job_id = uuid.uuid4().hex
        logger.info(f"Generated job_id: {job_id}")
        
        # Создаем директории для задачи
        job_dir = JOBS_DIR / job_id
        nifti_dir = job_dir / "nifti"
        
        for dir_path in [job_dir, nifti_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Сохраняем NIfTI файл
        nifti_path = nifti_dir / file.filename
        
        logger.info(f"Saving NIfTI file to {nifti_path}")
        
        # Читаем и сохраняем файл
        content = await file.read()
        with open(nifti_path, 'wb') as f:
            f.write(content)
        
        # Создаем status.json
        status_data = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "upload_filename": file.filename,
            "input_type": "nifti"
        }
        
        status_file = job_dir / "status.json"
        import json
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Запускаем pipeline в фоне
        logger.info(f"Starting background pipeline for job {job_id}")
        background_tasks.add_task(run_pipeline_with_input, job_id, str(nifti_path))
        
        logger.info(f"✅ NIfTI upload completed for job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "NIfTI file uploaded successfully. Processing started.",
            "input_type": "nifti"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NIfTI upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"NIfTI upload failed: {str(e)}"
        )
