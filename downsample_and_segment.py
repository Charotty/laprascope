#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging
import nibabel as nib
import numpy as np
from scipy.ndimage import zoom

# Добавляем путь к venv
sys.path.insert(0, str(Path(__file__).parent / ".venv" / "Lib" / "site-packages"))

try:
    from totalsegmentator.python_api import totalsegmentator
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def downsample_image(input_path, output_path, target_shape=(128, 128, 128)):
        """Уменьшаем размер изображения для экономии памяти"""
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
        
        # Сохраняем уменьшенное изображение
        new_img = nib.Nifti1Image(downsampled_data, img.affine)
        nib.save(new_img, output_path)
        logger.info(f"Saved downsampled image to {output_path}")
        
        return output_path
    
    def test_segmentation():
        input_path = "input/ct_scan.nii.gz"
        downsampled_path = "input/ct_scan_downsampled.nii.gz"
        output_path = "output"
        
        # Уменьшаем изображение
        downsample_image(input_path, downsampled_path, target_shape=(128, 128, 128))
        
        logger.info(f"Starting segmentation of {downsampled_path}")
        
        try:
            totalsegmentator(
                input=downsampled_path,
                output=output_path,
                ml=True,
                nr_thr_resamp=1,
                nr_thr_saving=1,
                roi_subset=["kidney_left", "kidney_right"],
                fast=True,
                device="cpu"
            )
            logger.info("Segmentation completed successfully!")
            
            # Проверяем результат
            output_files = list(Path(output_path).glob("*.nii.gz"))
            logger.info(f"Output files: {[f.name for f in output_files]}")
            
            for f in output_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                logger.info(f"  {f.name}: {size_mb:.2f} MB")
            
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            raise
    
    if __name__ == "__main__":
        test_segmentation()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure TotalSegmentator is installed correctly")
