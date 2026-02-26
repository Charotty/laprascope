"""
API endpoint для проверки статуса задач
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

from ..services.pipeline import get_job_status, list_jobs
from ..config import JOBS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status/{job_id}")
async def get_job_status_api(job_id: str) -> Dict:
    """
    Получает статус задачи по ID
    
    Args:
        job_id: ID задачи
        
    Returns:
        Dict: информация о статусе задачи
    """
    logger.info(f"Getting status for job {job_id}")
    
    try:
        # Получаем статус задачи
        status = get_job_status(job_id)
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Добавляем прогресс если возможно
        progress = calculate_progress(status)
        status["progress"] = progress
        
        logger.info(f"Job {job_id} status: {status['status']}, progress: {progress}%")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )

@router.get("/jobs")
async def list_all_jobs() -> Dict:
    """
    Получает список всех задач
    
    Returns:
        Dict: словарь со всеми задачами
    """
    logger.info("Getting list of all jobs")
    
    try:
        jobs = list_jobs()
        
        # Добавляем прогресс для каждой задачи
        for job_id, job_data in jobs.items():
            job_data["progress"] = calculate_progress(job_data)
        
        logger.info(f"Found {len(jobs)} jobs")
        
        return {
            "jobs": jobs,
            "total": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list jobs: {str(e)}"
        )

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> Dict:
    """
    Удаляет задачу и все связанные файлы
    
    Args:
        job_id: ID задачи
        
    Returns:
        Dict: результат удаления
    """
    logger.info(f"Deleting job {job_id}")
    
    try:
        job_dir = JOBS_DIR / job_id
        
        if not job_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Удаляем директорию задачи
        import shutil
        shutil.rmtree(job_dir)
        
        logger.info(f"✅ Job {job_id} deleted successfully")
        
        return {
            "job_id": job_id,
            "status": "deleted",
            "message": f"Job {job_id} and all associated files have been deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job: {str(e)}"
        )

def calculate_progress(status: Dict) -> int:
    """
    Рассчитывает процент выполнения задачи на основе статуса
    
    Args:
        status: данные о статусе задачи
        
    Returns:
        int: процент выполнения (0-100)
    """
    job_status = status.get("status", "pending")
    
    progress_map = {
        "pending": 0,
        "queued": 5,
        "processing": 25,
        "segmentation_done": 60,
        "conversion_done": 90,
        "completed": 100,
        "error": 0
    }
    
    base_progress = progress_map.get(job_status, 0)
    
    # Если есть дополнительная информация о прогрессе, используем ее
    if job_status == "processing" and "segmentation" in status:
        # Если сегментация началась, но не завершена
        base_progress = 35
    
    if job_status == "conversion_done" and "conversion" in status:
        # Проверяем, сколько органов успешно сконвертировано
        conversion = status.get("conversion", {})
        successful_conversions = sum(1 for organ in conversion.values() if "error" not in organ)
        total_organs = len(conversion)
        
        if total_organs > 0:
            conversion_progress = (successful_conversions / total_organs) * 30
            base_progress = 60 + conversion_progress
    
    return min(100, max(0, int(base_progress)))

@router.get("/health")
async def health_check() -> Dict:
    """
    Проверка здоровья API
    
    Returns:
        Dict: статус здоровья сервиса
    """
    try:
        # Проверяем доступность директорий
        jobs_accessible = JOBS_DIR.exists() and os.access(JOBS_DIR, os.R_OK | os.W_OK)
        
        # Проверяем количество активных задач
        jobs = list_jobs()
        active_jobs = sum(1 for job in jobs.values() 
                         if job.get("status") in ["queued", "processing", "segmentation_done"])
        
        return {
            "status": "healthy",
            "timestamp": str(Path().cwd()),
            "jobs_accessible": jobs_accessible,
            "active_jobs": active_jobs,
            "total_jobs": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/stats")
async def get_stats() -> Dict:
    """
    Получает статистику по задачам
    
    Returns:
        Dict: статистика
    """
    try:
        jobs = list_jobs()
        
        stats = {
            "total_jobs": len(jobs),
            "completed_jobs": 0,
            "failed_jobs": 0,
            "active_jobs": 0,
            "pending_jobs": 0
        }
        
        for job in jobs.values():
            status = job.get("status", "pending")
            if status == "completed":
                stats["completed_jobs"] += 1
            elif status == "error":
                stats["failed_jobs"] += 1
            elif status in ["queued", "processing", "segmentation_done", "conversion_done"]:
                stats["active_jobs"] += 1
            elif status == "pending":
                stats["pending_jobs"] += 1
        
        # Рассчитываем success rate
        total_finished = stats["completed_jobs"] + stats["failed_jobs"]
        stats["success_rate"] = (stats["completed_jobs"] / total_finished * 100) if total_finished > 0 else 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )
