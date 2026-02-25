"""
Модуль сегментации почек с использованием TotalSegmentator
"""
import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional
import json

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

try:
    from totalsegmentator.python_api import totalsegmentator
    import nibabel as nib
    import numpy as np
    from scipy.ndimage import zoom
except ImportError as e:
    logging.warning(f"Some ML packages not available: {e}")

logger = logging.getLogger(__name__)

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
    logger.info(f"Starting kidney segmentation for job {job_id}")
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {output_dir}")
    
    try:
        # Создаем выходную директорию
        os.makedirs(output_dir, exist_ok=True)
        
        # Определяем путь к выходным файлам
        kidney_left_path = os.path.join(output_dir, "kidney_left.nii.gz")
        kidney_right_path = os.path.join(output_dir, "kidney_right.nii.gz")
        
        # Проверяем, что входной файл существует
        if not os.path.exists(input_path):
            raise SegmentationError(f"Input file not found: {input_path}")
        
        # Определяем, нужно ли уменьшать изображение
        actual_input_path = input_path
        temp_files = []
        
        if use_downsampling and input_path.endswith('.nii.gz'):
            try:
                # Проверяем размер изображения
                img = nib.load(input_path)
                total_voxels = np.prod(img.shape)
                
                # Если изображение слишком большое, уменьшаем его
                if total_voxels > 50 * 1024 * 1024:  # > 50M вокселей
                    logger.info(f"Large image detected ({total_voxels} voxels), downsampling...")
                    actual_input_path = downsample_for_segmentation(input_path)
                    temp_files.append(actual_input_path)
                    
            except Exception as e:
                logger.warning(f"Failed to check image size: {e}")
        
        try:
            # Запускаем сегментацию
            logger.info("Running TotalSegmentator...")
            
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
            
            logger.info("Segmentation completed successfully!")
            
            # Проверяем результат
            results = {}
            
            if os.path.exists(kidney_left_path):
                left_img = nib.load(kidney_left_path)
                left_data = left_img.get_fdata()
                left_voxels = np.sum(left_data > 0)
                left_size_mb = os.path.getsize(kidney_left_path) / (1024 * 1024)
                
                results["kidney_left"] = {
                    "file": "kidney_left.nii.gz",
                    "voxels": int(left_voxels),
                    "size_mb": round(left_size_mb, 2),
                    "shape": list(left_img.shape)
                }
                logger.info(f"Left kidney: {left_voxels} voxels, {left_size_mb:.2f} MB")
            else:
                logger.warning("Left kidney segmentation not found")
                results["kidney_left"] = {"error": "Segmentation not found"}
            
            if os.path.exists(kidney_right_path):
                right_img = nib.load(kidney_right_path)
                right_data = right_img.get_fdata()
                right_voxels = np.sum(right_data > 0)
                right_size_mb = os.path.getsize(kidney_right_path) / (1024 * 1024)
                
                results["kidney_right"] = {
                    "file": "kidney_right.nii.gz",
                    "voxels": int(right_voxels),
                    "size_mb": round(right_size_mb, 2),
                    "shape": list(right_img.shape)
                }
                logger.info(f"Right kidney: {right_voxels} voxels, {right_size_mb:.2f} MB")
            else:
                logger.warning("Right kidney segmentation not found")
                results["kidney_right"] = {"error": "Segmentation not found"}
            
            # Сохраняем статус задачи
            status_file = os.path.join(output_dir, "status.json")
            status_data = {
                "job_id": job_id,
                "status": "completed",
                "segmentation": results
            }
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            
            return {
                "status": "success",
                "job_id": job_id,
                "results": results
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
        
    except subprocess.CalledProcessError as e:
        error_msg = f"TotalSegmentator failed with exit code {e.returncode}"
        logger.error(error_msg)
        raise SegmentationError(error_msg)
        
    except MemoryError as e:
        error_msg = "Memory error during segmentation - try smaller image or more RAM"
        logger.error(error_msg)
        raise SegmentationError(error_msg)
        
    except Exception as e:
        error_msg = f"Segmentation failed: {str(e)}"
        logger.error(error_msg)
        
        # Сохраняем статус ошибки
        try:
            status_file = os.path.join(output_dir, "status.json")
            status_data = {
                "job_id": job_id,
                "status": "error",
                "error": error_msg
            }
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
        except Exception as save_error:
            logger.error(f"Failed to save error status: {save_error}")
        
        raise SegmentationError(error_msg)

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
