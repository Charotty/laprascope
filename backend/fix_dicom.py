#!/usr/bin/env python3
"""
Скрипт для предобработки проблемных DICOM файлов
"""
import os
import pydicom
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def fix_dicom_orientation(dicom_dir: str, output_dir: str) -> bool:
    """
    Пытается исправить проблемы с ориентацией DICOM файлов
    """
    try:
        dicom_path = Path(dicom_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Получаем все DICOM файлы
        dicom_files = []
        for file_path in dicom_path.glob("*.dcm"):
            try:
                ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
                dicom_files.append((file_path, ds))
            except:
                continue
                
        if not dicom_files:
            return False
            
        # Сортируем по номеру среза
        dicom_files.sort(key=lambda x: float(x[1].get('SliceLocation', 0)))
        
        # Копируем только файлы с согласованной ориентацией
        valid_files = []
        reference_orientation = None
        
        for file_path, ds in dicom_files:
            try:
                orientation = ds.get('ImageOrientationPatient', None)
                if orientation is None:
                    continue
                    
                if reference_orientation is None:
                    reference_orientation = orientation
                    valid_files.append(file_path)
                else:
                    # Проверяем сходство ориентации
                    if all(abs(a - b) < 0.1 for a, b in zip(orientation, reference_orientation)):
                        valid_files.append(file_path)
                    else:
                        logger.warning(f"Skipping inconsistent slice: {file_path}")
                        
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
                continue
        
        # Копируем валидные файлы
        for file_path in valid_files:
            shutil.copy2(file_path, output_path / file_path.name)
            
        logger.info(f"Fixed DICOM orientation: {len(valid_files)}/{len(dicom_files)} files kept")
        return len(valid_files) > 0
        
    except Exception as e:
        logger.error(f"Failed to fix DICOM orientation: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python fix_dicom.py <input_dir> <output_dir>")
        sys.exit(1)
        
    success = fix_dicom_orientation(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
