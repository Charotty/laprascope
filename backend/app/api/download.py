"""
API endpoint для скачивания STL файлов
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

from ..services.pipeline import get_job_status
from ..config import JOBS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stl/{job_id}/{organ}")
async def download_stl(job_id: str, organ: str):
    """
    Скачивает STL файл конкретного органа
    
    Args:
        job_id: ID задачи
        organ: название органа ('kidney_left' или 'kidney_right')
        
    Returns:
        FileResponse: STL файл
    """
    logger.info(f"Downloading STL for job {job_id}, organ {organ}")
    
    try:
        # Проверяем валидность названия органа
        valid_organs = ['kidney_left', 'kidney_right']
        if organ not in valid_organs:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid organ. Must be one of: {valid_organs}"
            )
        
        # Проверяем существование задачи
        job_status = get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Проверяем статус задачи
        if job_status.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed. Current status: {job_status.get('status')}"
            )
        
        # Формируем путь к STL файлу
        stl_path = JOBS_DIR / job_id / "stl" / f"{organ}.stl"
        
        # Проверяем существование файла
        if not stl_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"STL file for {organ} not found"
            )
        
        # Проверяем размер файла
        file_size = stl_path.stat().st_size
        if file_size == 0:
            raise HTTPException(
                status_code=500,
                detail=f"STL file for {organ} is empty"
            )
        
        logger.info(f"Serving STL file: {stl_path} ({file_size} bytes)")
        
        # Возвращаем файл с правильными заголовками
        return FileResponse(
            path=str(stl_path),
            media_type="model/stl",
            filename=f"{job_id}_{organ}.stl",
            headers={
                "Content-Disposition": f"attachment; filename={job_id}_{organ}.stl",
                "Content-Length": str(file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download STL for job {job_id}, organ {organ}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download STL file: {str(e)}"
        )

@router.get("/nifti/{job_id}/{organ}")
async def download_nifti(job_id: str, organ: str):
    """
    Скачивает NIfTI файл конкретного органа
    
    Args:
        job_id: ID задачи
        organ: название органа ('kidney_left' или 'kidney_right')
        
    Returns:
        FileResponse: NIfTI файл
    """
    logger.info(f"Downloading NIfTI for job {job_id}, organ {organ}")
    
    try:
        # Проверяем валидность названия органа
        valid_organs = ['kidney_left', 'kidney_right']
        if organ not in valid_organs:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid organ. Must be one of: {valid_organs}"
            )
        
        # Проверяем существование задачи
        job_status = get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Проверяем, что сегментация завершена
        if job_status.get("status") not in ["segmentation_done", "conversion_done", "completed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Segmentation not completed for job {job_id}. Current status: {job_status.get('status')}"
            )
        
        # Формируем путь к NIfTI файлу
        nifti_path = JOBS_DIR / job_id / "nifti" / f"{organ}.nii.gz"
        
        # Проверяем существование файла
        if not nifti_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"NIfTI file for {organ} not found"
            )
        
        # Проверяем размер файла
        file_size = nifti_path.stat().st_size
        if file_size == 0:
            raise HTTPException(
                status_code=500,
                detail=f"NIfTI file for {organ} is empty"
            )
        
        logger.info(f"Serving NIfTI file: {nifti_path} ({file_size} bytes)")
        
        # Возвращаем файл с правильными заголовками
        return FileResponse(
            path=str(nifti_path),
            media_type="application/gzip",
            filename=f"{job_id}_{organ}.nii.gz",
            headers={
                "Content-Disposition": f"attachment; filename={job_id}_{organ}.nii.gz",
                "Content-Length": str(file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download NIfTI for job {job_id}, organ {organ}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download NIfTI file: {str(e)}"
        )

@router.get("/download/{job_id}/all")
async def download_all_files(job_id: str):
    """
    Скачивает все файлы задачи в ZIP архиве
    
    Args:
        job_id: ID задачи
        
    Returns:
        FileResponse: ZIP архив со всеми файлами
    """
    logger.info(f"Downloading all files for job {job_id}")
    
    try:
        # Проверяем существование задачи
        job_status = get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Проверяем статус задачи
        if job_status.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed. Current status: {job_status.get('status')}"
            )
        
        job_dir = JOBS_DIR / job_id
        
        # Создаем ZIP архив
        import zipfile
        import tempfile
        
        zip_path = Path(tempfile.gettempdir()) / f"{job_id}_all_files.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем все файлы из директории задачи
            for file_path in job_dir.rglob("*"):
                if file_path.is_file():
                    # Сохраняем структуру директорий
                    arcname = file_path.relative_to(job_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Created ZIP archive: {zip_path}")
        
        # Возвращаем ZIP файл
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"{job_id}_all_files.zip",
            headers={
                "Content-Disposition": f"attachment; filename={job_id}_all_files.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create ZIP for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create ZIP archive: {str(e)}"
        )

@router.get("/files/{job_id}")
async def list_job_files(job_id: str) -> Dict:
    """
    Получает список всех файлов задачи
    
    Args:
        job_id: ID задачи
        
    Returns:
        Dict: список файлов с информацией
    """
    logger.info(f"Listing files for job {job_id}")
    
    try:
        # Проверяем существование задачи
        job_status = get_job_status(job_id)
        if job_status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_dir = JOBS_DIR / job_id
        
        if not job_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Job directory not found"
            )
        
        files = {}
        
        # Сканируем все файлы
        for file_path in job_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(job_dir)
                file_info = {
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
                }
                files[str(relative_path)] = file_info
        
        logger.info(f"Found {len(files)} files for job {job_id}")
        
        return {
            "job_id": job_id,
            "files": files,
            "total_files": len(files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )
