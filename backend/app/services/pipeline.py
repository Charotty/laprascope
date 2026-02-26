"""
Оркестратор pipeline для обработки DICOM/NIfTI файлов
"""
import os
import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

from services.segmentation import segment_kidneys, SegmentationError
from services.conversion import convert_organ_to_stl, ConversionError
from config import DATA_DIR, JOBS_DIR, ML_CONFIG

logger = logging.getLogger(__name__)

class PipelineError(Exception):
    """Исключения для ошибок pipeline"""
    pass

class JobStatus:
    """Статусы задач"""
    PENDING = "pending"
    PROCESSING = "processing"
    SEGMENTATION_DONE = "segmentation_done"
    CONVERSION_DONE = "conversion_done"
    COMPLETED = "completed"
    ERROR = "error"

def update_job_status(job_id: str, status: str, details: Optional[Dict] = None) -> None:
    """
    Обновляет статус задачи в файле status.json
    
    Args:
        job_id: ID задачи
        status: новый статус
        details: дополнительная информация
    """
    job_dir = JOBS_DIR / job_id
    status_file = job_dir / "status.json"
    
    status_data = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.now().isoformat(),
    }
    
    if details:
        status_data.update(details)
    
    # Создаем директорию если нужно
    job_dir.mkdir(exist_ok=True)
    
    # Сохраняем статус
    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)
    
    logger.info(f"Updated job {job_id} status to {status}")

def get_job_status(job_id: str) -> Optional[Dict]:
    """
    Получает статус задачи
    
    Args:
        job_id: ID задачи
        
    Returns:
        Optional[Dict]: данные о статусе задачи или None
    """
    status_file = JOBS_DIR / job_id / "status.json"
    
    if not status_file.exists():
        return None
    
    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read status for job {job_id}: {e}")
        return None

def run_pipeline(job_id: str, input_path: str) -> Dict:
    """
    Запускает полный pipeline обработки
    
    Args:
        job_id: уникальный идентификатор задачи
        input_path: путь к входному файлу (NIfTI или DICOM папка)
        
    Returns:
        Dict: результат выполнения pipeline
    """
    logger.info(f"Starting pipeline for job {job_id}")
    logger.info(f"Input: {input_path}")
    
    try:
        # Создаем структуру директорий для задачи
        job_dir = JOBS_DIR / job_id
        dicom_dir = job_dir / "dicom"
        nifti_dir = job_dir / "nifti"
        stl_dir = job_dir / "stl"
        
        for dir_path in [job_dir, dicom_dir, nifti_dir, stl_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Шаг 1: Обновить статус → processing
        update_job_status(job_id, JobStatus.PROCESSING, {
            "input_path": input_path,
            "started_at": datetime.now().isoformat()
        })
        
        # Шаг 2: Сегментация
        logger.info("Step 2: Running segmentation...")
        try:
            segmentation_result = segment_kidneys(job_id, input_path, str(nifti_dir))
            
            update_job_status(job_id, JobStatus.SEGMENTATION_DONE, {
                "segmentation": segmentation_result.get("results", {}),
                "segmentation_completed_at": datetime.now().isoformat()
            })
            
        except SegmentationError as e:
            update_job_status(job_id, JobStatus.ERROR, {
                "error": str(e),
                "error_type": "segmentation",
                "failed_at": datetime.now().isoformat()
            })
            raise PipelineError(f"Segmentation failed: {e}")
        
        # Шаг 3: Конвертация в STL
        logger.info("Step 3: Converting to STL...")
        conversion_results = {}
        
        try:
            organs = ["kidney_left", "kidney_right"]
            target_faces = ML_CONFIG["target_faces"]
            
            for organ in organs:
                organ_stl_path = convert_organ_to_stl(
                    job_id, organ, str(nifti_dir), str(stl_dir), target_faces
                )
                
                if organ_stl_path:
                    # Проверяем размер файла
                    file_size_mb = os.path.getsize(organ_stl_path) / (1024 * 1024)
                    conversion_results[organ] = {
                        "stl_file": os.path.basename(organ_stl_path),
                        "size_mb": round(file_size_mb, 2),
                        "path": organ_stl_path
                    }
                    logger.info(f"✅ {organ}: {file_size_mb:.2f} MB")
                else:
                    conversion_results[organ] = {
                        "error": "Conversion failed"
                    }
                    logger.warning(f"❌ {organ}: conversion failed")
            
            update_job_status(job_id, JobStatus.CONVERSION_DONE, {
                "conversion": conversion_results,
                "conversion_completed_at": datetime.now().isoformat()
            })
            
        except ConversionError as e:
            update_job_status(job_id, JobStatus.ERROR, {
                "error": str(e),
                "error_type": "conversion",
                "failed_at": datetime.now().isoformat()
            })
            raise PipelineError(f"Conversion failed: {e}")
        
        # Шаг 4: Очистка исходных файлов
        logger.info("Step 4: Cleaning up input files...")
        try:
            # Удаляем DICOM директорию, если она есть
            if dicom_dir.exists():
                shutil.rmtree(dicom_dir)
                logger.info(f"✅ Removed DICOM directory: {dicom_dir}")
            
            # Для NIfTI загрузок удаляем только исходный файл, но оставляем результаты сегментации
            # (kidney_left.nii.gz и kidney_right.nii.gz)
            # Исходный NIfTI файл обычно имеет имя, отличное от kidney_*.nii.gz
            if nifti_dir.exists():
                input_nifti_files = [
                    f for f in nifti_dir.iterdir() 
                    if f.is_file() and not f.name.startswith('kidney_')
                ]
                for orig_file in input_nifti_files:
                    orig_file.unlink()
                    logger.info(f"✅ Removed original NIfTI file: {orig_file}")
                    
        except Exception as cleanup_err:
            logger.warning(f"⚠️ Failed to clean up input files: {cleanup_err}")
            # Не прерываем pipeline из-за ошибки очистки
        
        # Шаг 5: Завершение
        logger.info("Step 5: Pipeline completed!")
        
        final_result = {
            "job_id": job_id,
            "status": JobStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "segmentation": segmentation_result.get("results", {}),
            "conversion": conversion_results,
            "files": {
                "nifti_dir": str(nifti_dir),
                "stl_dir": str(stl_dir)
            },
            "cleanup_completed": True
        }
        
        update_job_status(job_id, JobStatus.COMPLETED, final_result)
        
        logger.info(f"✅ Pipeline completed successfully for job {job_id}")
        return final_result
        
    except PipelineError:
        raise
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}"
        logger.error(error_msg)
        
        update_job_status(job_id, JobStatus.ERROR, {
            "error": error_msg,
            "error_type": "pipeline",
            "failed_at": datetime.now().isoformat()
        })
        
        raise PipelineError(error_msg)

def create_job(input_path: str) -> str:
    """
    Создает новую задачу
    
    Args:
        input_path: путь к входному файлу
        
    Returns:
        str: ID созданной задачи
    """
    # Генерируем уникальный ID
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    
    # Проверяем, что входной файл существует
    if not os.path.exists(input_path):
        raise PipelineError(f"Input file not found: {input_path}")
    
    # Создаем задачу со статусом pending
    update_job_status(job_id, JobStatus.PENDING, {
        "input_path": input_path,
        "created_at": datetime.now().isoformat()
    })
    
    logger.info(f"Created job {job_id} for input {input_path}")
    return job_id

def list_jobs() -> Dict[str, Dict]:
    """
    Получает список всех задач
    
    Returns:
        Dict[str, Dict]: словарь с информацией о задачах
    """
    jobs = {}
    
    if not JOBS_DIR.exists():
        return jobs
    
    for job_dir in JOBS_DIR.iterdir():
        if job_dir.is_dir():
            status = get_job_status(job_dir.name)
            if status:
                jobs[job_dir.name] = status
    
    return jobs

if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Создаем тестовую задачу
        test_input = "input/kidney_test.nii.gz"
        job_id = create_job(test_input)
        
        print(f"Created job: {job_id}")
        
        # Запускаем pipeline
        result = run_pipeline(job_id, test_input)
        print(f"Pipeline result: {result}")
        
    except PipelineError as e:
        print(f"Pipeline failed: {e}")
