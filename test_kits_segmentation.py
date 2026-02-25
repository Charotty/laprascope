#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging
import time

# Добавляем путь к venv
venv_path = Path(__file__).parent / ".venv"
if sys.platform == "win32":
    sys.path.insert(0, str(venv_path / "Lib" / "site-packages"))
else:
    sys.path.insert(0, str(venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"))

try:
    import nibabel as nib
    import numpy as np
    from scipy.ndimage import zoom
    from totalsegmentator.python_api import totalsegmentator
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def downsample_for_segmentation(input_path, target_shape=(128, 128, 128)):
        """Уменьшаем размер изображения для сегментации"""
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
        
        return new_img
    
    def test_kits_segmentation():
        input_path = "kits23/dataset/case_00000/segmentation.nii.gz"
        output_path = "output"
        
        # Создаем папку output если нет
        os.makedirs(output_path, exist_ok=True)
        
        logger.info(f"Starting segmentation of {input_path}")
        start_time = time.time()
        
        # Уменьшаем изображение
        downsampled_img = downsample_for_segmentation(input_path, target_shape=(128, 128, 128))
        
        # Сохраняем временное уменьшенное изображение
        temp_input = "input/temp_kits_downsampled.nii.gz"
        os.makedirs("input", exist_ok=True)
        nib.save(downsampled_img, temp_input)
        
        try:
            # Запускаем сегментацию с уменьшенным изображением
            totalsegmentator(
                input=temp_input,
                output=output_path,
                ml=True,
                nr_thr_resamp=1,
                nr_thr_saving=1,
                roi_subset=["kidney_left", "kidney_right"],
                fast=True,
                device="cpu"
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            logger.info(f"Segmentation completed successfully!")
            logger.info(f"Execution time: {execution_time:.2f} seconds")
            
            # Проверяем результат
            output_files = list(Path(output_path).glob("*.nii.gz"))
            logger.info(f"Output files: {[f.name for f in output_files]}")
            
            for f in output_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                logger.info(f"  {f.name}: {size_mb:.2f} MB")
            
            return execution_time
            
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            raise
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_input):
                os.remove(temp_input)
    
    if __name__ == "__main__":
        test_kits_segmentation()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure TotalSegmentator is installed correctly")
