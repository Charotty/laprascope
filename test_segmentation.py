#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging

# Добавляем путь к venv
sys.path.insert(0, str(Path(__file__).parent / ".venv" / "Lib" / "site-packages"))

try:
    from totalsegmentator.python_api import totalsegmentator
    import nibabel as nib
    import numpy as np
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def test_segmentation():
        input_path = "input/ct_scan.nii.gz"
        output_path = "output"
        
        logger.info(f"Starting segmentation of {input_path}")
        
        # Проверяем размер входного файла
        img = nib.load(input_path)
        logger.info(f"Input shape: {img.shape}, dtype: {img.get_fdata().dtype}")
        
        # Запускаем сегментацию с минимальными параметрами
        try:
            totalsegmentator(
                input=input_path,
                output=output_path,
                ml=True,  # Используем CPU вместо GPU если не хватает памяти
                nr_thr_resamp=1,  # Один поток для уменьшения памяти
                nr_thr_saving=1,
                roi_subset=["kidney_left", "kidney_right"],
                fast=True,
                device="cpu"  # Принудительно CPU
            )
            logger.info("Segmentation completed successfully!")
            
            # Проверяем результат
            output_files = list(Path(output_path).glob("*.nii.gz"))
            logger.info(f"Output files: {output_files}")
            
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            raise
    
    if __name__ == "__main__":
        test_segmentation()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure TotalSegmentator is installed correctly")
