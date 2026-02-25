#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import logging
import numpy as np
import pydicom
import nibabel as nib

# Добавляем путь к venv
sys.path.insert(0, str(Path(__file__).parent / ".venv" / "Lib" / "site-packages"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_dicom_to_nifti(input_dir, output_file, max_slices=200):
    """
    Простая конвертация DICOM в NIfTI без сложной логики
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
        step = len(dicom_files) // max_slices
        selected_files = dicom_files[::step][:max_slices]
        logger.info(f"Using {len(selected_files)} slices (every {step}th slice)")
    else:
        selected_files = dicom_files
    
    # Читаем первый DICOM для получения метаданных
    first_ds = pydicom.dcmread(selected_files[0])
    
    # Получаем размеры изображения
    rows = first_ds.Rows
    cols = first_ds.Columns
    num_slices = len(selected_files)
    
    logger.info(f"Image dimensions: {rows} x {cols} x {num_slices}")
    
    # Создаем 3D массив
    volume = np.zeros((num_slices, rows, cols), dtype=np.int16)
    
    # Читаем все срезы
    for i, file_path in enumerate(selected_files):
        try:
            ds = pydicom.dcmread(file_path)
            volume[i] = ds.pixel_array
            
            if i % 50 == 0:
                logger.info(f"Processed slice {i+1}/{num_slices}")
                
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            continue
    
    # Получаем информацию о пространственном разрешении
    pixel_spacing = first_ds.PixelSpacing
    slice_thickness = float(first_ds.SliceThickness) if hasattr(first_ds, 'SliceThickness') else 1.0
    
    # Создаем affine матрицу
    affine = np.eye(4)
    affine[0, 0] = pixel_spacing[0]  # x spacing
    affine[1, 1] = pixel_spacing[1]  # y spacing  
    affine[2, 2] = slice_thickness    # z spacing
    
    # Создаем NIfTI изображение
    nifti_img = nib.Nifti1Image(volume, affine)
    
    # Сохраняем
    nib.save(nifti_img, output_file)
    logger.info(f"Successfully saved to {output_file}")
    
    # Проверяем результат
    img = nib.load(output_file)
    logger.info(f"Output shape: {img.shape}, dtype: {img.get_fdata().dtype}")
    logger.info(f"Affine:\n{img.affine}")
    
    return output_file

if __name__ == "__main__":
    input_dir = "D:/DICOM СНИМКИ/Андреев Д.А/КТ/25021714"
    output_file = "input/ct_scan_from_dicom.nii.gz"
    
    # Создаем папку input если нет
    os.makedirs("input", exist_ok=True)
    
    # Конвертируем
    simple_dicom_to_nifti(input_dir, output_file, max_slices=200)
    
    logger.info("Conversion completed!")
