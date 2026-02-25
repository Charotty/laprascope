#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging
import nibabel as nib
import numpy as np
from pydicom import dcmread
import pydicom
from datetime import datetime

# Добавляем путь к venv
sys.path.insert(0, str(Path(__file__).parent / ".venv" / "Lib" / "site-packages"))

try:
    import dicom2nifti
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def convert_dicom_subset(input_dir, output_file, max_slices=500):
        """
        Конвертирует подмножество DICOM файлов в NIfTI для экономии памяти
        """
        logger.info(f"Converting DICOM from {input_dir}")
        
        # Получаем все DICOM файлы
        dicom_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.isdigit():  # DICOM файлы имеют числовые имена
                    dicom_files.append(os.path.join(root, file))
        
        dicom_files.sort()
        logger.info(f"Found {len(dicom_files)} DICOM files")
        
        # Ограничиваем количество срезов
        if len(dicom_files) > max_slices:
            # Берем равномерно распределенные срезы
            step = len(dicom_files) // max_slices
            selected_files = dicom_files[::step][:max_slices]
            logger.info(f"Using {len(selected_files)} slices (every {step}th slice)")
        else:
            selected_files = dicom_files
        
        # Создаем временную папку для выбранных файлов
        temp_dir = Path("temp_dicom_subset")
        temp_dir.mkdir(exist_ok=True)
        
        # Копируем выбранные файлы
        for i, file_path in enumerate(selected_files):
            dest = temp_dir / f"{i:06d}"
            import shutil
            shutil.copy2(file_path, dest)
        
        try:
            # Конвертируем подмножество
            logger.info(f"Converting {len(selected_files)} DICOM files to NIfTI...")
            dicom2nifti.dicom_series_to_nifti(str(temp_dir), output_file, reorient_nifti=True)
            logger.info(f"Successfully converted to {output_file}")
            
            # Проверяем результат
            img = nib.load(output_file)
            logger.info(f"Output shape: {img.shape}, dtype: {img.get_fdata().dtype}")
            
            return output_file
            
        finally:
            # Очищаем временную папку
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    if __name__ == "__main__":
        input_dir = "D:/DICOM СНИМКИ/Андреев Д.А/КТ/25021714"
        output_file = "input/ct_scan_from_dicom.nii.gz"
        
        # Создаем папку input если нет
        os.makedirs("input", exist_ok=True)
        
        # Конвертируем с ограничением памяти
        convert_dicom_subset(input_dir, output_file, max_slices=500)
        
        logger.info("Conversion completed!")
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure required packages are installed")
