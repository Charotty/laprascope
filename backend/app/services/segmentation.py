"""
Модуль сегментации почек с использованием TotalSegmentator
"""
import os
import sys
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Импортируем патчи для совместимости с PyTorch 2.6
from ..pytorch_patch import apply_all_patches

# Применяем патчи до импорта totalsegmentator
apply_all_patches()

# Импортируем патч для обхода проблем с DICOM валидацией
from ..dicom_patch import patch_dicom2nifti

# Применяем патч до импорта totalsegmentator
patch_dicom2nifti()

import nibabel as nib
import numpy as np
from totalsegmentator.python_api import totalsegmentator
import subprocess
from scipy.ndimage import zoom

# Импортируем наши модули
from ..utils.logging_config import get_logger, measure_time
from ..utils.errors import processing_error, memory_error, handle_exception

logger = get_logger(__name__)

class SegmentationError(Exception):
    """Исключения для ошибок сегментации"""
    pass

def downsample_for_segmentation(input_path: str, target_shape: tuple = (128, 128, 128)) -> str:
    """
    Уменьшает размер изображения для экономии памяти
    
    Args:
        input_path: путь к входному NIfTI файлу
        target_shape: целевые размеры изображения
        
    Returns:
        str: путь к уменьшенному изображению
    """
    logger.info(f"Loading image from {input_path}")
    img = nib.load(input_path)
    data = img.get_fdata()
    
    logger.info(f"Original shape: {data.shape}")
    
    # Вычисляем коэффициенты даунсэмплинга
    zoom_factors = [target_shape[i] / data.shape[i] for i in range(3)]
    logger.info(f"Zoom factors: {zoom_factors}")
    
    # Уменьшаем изображение
    downsampled_data = zoom(data, zoom_factors, order=1)
    logger.info(f"Downsampled shape: {downsampled_data.shape}")
    
    # Создаем новое изображение с тем же affine
    new_img = nib.Nifti1Image(downsampled_data, img.affine)
    
    # Сохраняем временное уменьшенное изображение
    temp_input = input_path.replace('.nii.gz', '_downsampled.nii.gz')
    nib.save(new_img, temp_input)
    
    return temp_input

def validate_segmentation_quality(img_path: str, organ_name: str) -> Dict:
    """
    Проверяет качество сегментации
    
    Args:
        img_path: путь к сегментированному файлу
        organ_name: название органа для логов
        
    Returns:
        Dict: результат валидации
    """
    try:
        img = nib.load(img_path)
        data = img.get_fdata()
        
        # Базовые проверки
        total_voxels = np.sum(data > 0)
        file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
        
        # Проверки качества
        quality_issues = []
        
        # 1. Проверка на пустую маску
        if total_voxels == 0:
            quality_issues.append("Empty segmentation mask")
        
        # 2. Проверка на слишком маленькую сегментацию (<100 вокселей)
        elif total_voxels < 100:
            quality_issues.append(f"Very small segmentation: {total_voxels} voxels")
        
        # 3. Проверка на слишком большой файл (>100MB для одной почки)
        if file_size_mb > 100:
            quality_issues.append(f"Oversized file: {file_size_mb:.1f}MB")
        
        # 4. Проверка на аномальные размеры
        if np.any(np.array(data.shape) > 1000):
            quality_issues.append(f"Anomalous dimensions: {data.shape}")
        
        # 5. Проверка на наличие NaN или inf значений
        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            quality_issues.append("Invalid values (NaN/Inf) in segmentation")
        
        return {
            "valid": len(quality_issues) == 0,
            "voxels": int(total_voxels),
            "size_mb": round(file_size_mb, 2),
            "shape": list(data.shape),
            "issues": quality_issues,
            "organ": organ_name
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "organ": organ_name
        }

def segment_kidneys(job_id: str, input_path: str, output_dir: str, use_downsampling: bool = True) -> Dict:
    """
    Сегментация почек с использованием TotalSegmentator
    
    Args:
        job_id: уникальный идентификатор задачи
        input_path: путь к входному файлу (NIfTI или DICOM папка)
        output_dir: директория для сохранения результатов
        use_downsampling: использовать ли уменьшение размера изображения
        
    Returns:
        Dict: результат сегментации со статусом и информацией
    """
    with measure_time(logger, f"kidney segmentation", {"job_id": job_id}):
        try:
            logger.info(f"Starting kidney segmentation for job {job_id}")
            logger.info(f"Input: {input_path}")
            logger.info(f"Output: {output_dir}")
            
            # Создаем выходную директорию
            os.makedirs(output_dir, exist_ok=True)
            actual_input_path = input_path
        
        # Проверяем размер файла
        if os.path.isfile(actual_input_path):
            file_size = os.path.getsize(actual_input_path) / (1024 * 1024)  # MB
            logger.info(f"📊 NIfTI file size: {file_size:.2f} MB")
            
            if file_size > 1000:  # > 1GB
                logger.warning("⚠️ Large file detected, this may take a long time")
        
        # Создаем выходную директорию
        os.makedirs(output_dir, exist_ok=True)
        
        # Определяем путь к выходным файлам
        kidney_left_path = os.path.join(output_dir, "kidney_left.nii.gz")
        kidney_right_path = os.path.join(output_dir, "kidney_right.nii.gz")
        
        # Запускаем сегментацию с таймаутом
        import signal
        import subprocess
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Segmentation timed out after 30 minutes")
        
        # Устанавливаем таймаут
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1800)  # 30 минут
        
        try:
            logger.info("🚀 Starting TotalSegmentator...")
            totalsegmentator(
                input=actual_input_path,
                output=output_dir,
                ml=True,
                nr_thr_resamp=1,
                nr_thr_saving=1,
                roi_subset=["kidney_left", "kidney_right"],
                fast=True,
                device="cpu"
            )
            signal.alarm(0)  # Отменяем таймаут
        except TimeoutError:
            logger.error("⏰ Segmentation timed out after 30 minutes")
            raise processing_error(
                "Segmentation timed out. The DICOM file may be too large or corrupted.",
                details={"job_id": job_id, "timeout": "30 minutes"}
            )
        
        # Проверяем результат
        if not os.path.exists(kidney_left_path) and not os.path.exists(kidney_right_path):
            raise FileNotFoundError("No kidney segmentation results found")
        
        # Проверяем качество сегментации
        results = {}
        
        # Валидация левой почки
        if os.path.exists(kidney_left_path):
            left_validation = validate_segmentation_quality(kidney_left_path, "kidney_left")
            if left_validation["valid"]:
                results["kidney_left"] = {
                    "file": "kidney_left.nii.gz",
                    "voxels": left_validation["voxels"],
                    "size_mb": left_validation["size_mb"],
                    "shape": left_validation["shape"],
                    "quality": "good"
                }
                logger.info(f"✅ Left kidney: {left_validation['voxels']} voxels, {left_validation['size_mb']:.2f} MB")
                    results["kidney_left"] = {
                        "error": "Poor quality segmentation",
                        "issues": left_validation.get("issues", left_validation.get("error", "Unknown error")),
                        "quality": "poor"
                    }
                    logger.warning(f"❌ Left kidney quality issues: {left_validation.get('issues', left_validation.get('error'))}")
            else:
                logger.warning("Left kidney segmentation not found")
                results["kidney_left"] = {"error": "Segmentation not found", "quality": "missing"}
            
            # Валидация правой почки
            if os.path.exists(kidney_right_path):
                right_validation = validate_segmentation_quality(kidney_right_path, "kidney_right")
                if right_validation["valid"]:
                    results["kidney_right"] = {
                        "file": "kidney_right.nii.gz",
                        "voxels": right_validation["voxels"],
                        "size_mb": right_validation["size_mb"],
                        "shape": right_validation["shape"],
                        "quality": "good"
                    }
                    logger.info(f"✅ Right kidney: {right_validation['voxels']} voxels, {right_validation['size_mb']:.2f} MB")
                else:
                    results["kidney_right"] = {
                        "error": "Poor quality segmentation",
                        "issues": right_validation.get("issues", right_validation.get("error", "Unknown error")),
                        "quality": "poor"
                    }
                    logger.warning(f"❌ Right kidney quality issues: {right_validation.get('issues', right_validation.get('error'))}")
            else:
                logger.warning("Right kidney segmentation not found")
                results["kidney_right"] = {"error": "Segmentation not found", "quality": "missing"}
            
            # Общая оценка качества
            quality_summary = {
                "total_organs": len(results),
                "good_quality": len([r for r in results.values() if r.get("quality") == "good"]),
                "poor_quality": len([r for r in results.values() if r.get("quality") == "poor"]),
                "missing": len([r for r in results.values() if r.get("quality") == "missing"])
            }
            
            logger.info(f"Quality summary: {quality_summary['good_quality']} good, {quality_summary['poor_quality']} poor, {quality_summary['missing']} missing")
            
            # Если обе почки имеют плохое качество или отсутствуют, считаем сегментацию неудачной
            if quality_summary["good_quality"] == 0:
                raise processing_error(
                    f"No valid segmentation results. Quality summary: {quality_summary}",
                    details={"job_id": job_id, "quality_summary": quality_summary}
                )
            
            return {
                "results": results,
                "quality_summary": quality_summary,
                "success": quality_summary["good_quality"] > 0
            }
            
        finally:
            # Удаляем временные файлы
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.info(f"Removed temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {e}")

if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)
    
    test_job_id = "test_001"
    test_input = "input/kidney_test.nii.gz"
    test_output = "data/jobs/test_001"
    
    try:
        result = segment_kidneys(test_job_id, test_input, test_output)
        print(f"Test completed: {result}")
    except SegmentationError as e:
        print(f"Test failed: {e}")
