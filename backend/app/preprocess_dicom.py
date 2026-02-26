#!/usr/bin/env python3
"""
Скрипт для исправления проблемных DICOM файлов перед сегментацией
"""
import os
import shutil
import pydicom
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def fix_dicom_orientation_issue(dicom_dir: str, output_dir: str) -> bool:
    """
    Исправляет DICOM файлы с проблемами ориентации
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
            except Exception as e:
                logger.warning(f"Cannot read {file_path}: {e}")
                continue
                
        if len(dicom_files) < 10:
            logger.warning(f"Too few DICOM files: {len(dicom_files)}")
            return False
            
        # Группируем по ориентации
        orientation_groups = {}
        
        for file_path, ds in dicom_files:
            try:
                orientation = ds.get('ImageOrientationPatient', None)
                if orientation is None:
                    continue
                    
                # Округляем ориентацию для группировки
                orientation_rounded = tuple(round(float(x), 1) for x in orientation)
                
                if orientation_rounded not in orientation_groups:
                    orientation_groups[orientation_rounded] = []
                orientation_groups[orientation_rounded].append((file_path, ds))
                
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
                continue
        
        # Находим самую большую группу (основная ориентация)
        if not orientation_groups:
            logger.error("No valid orientation groups found")
            return False
            
        main_orientation = max(orientation_groups.keys(), key=lambda k: len(orientation_groups[k]))
        main_files = orientation_groups[main_orientation]
        
        logger.info(f"Found {len(orientation_groups)} orientation groups")
        logger.info(f"Main orientation: {main_orientation} with {len(main_files)} files")
        
        # Копируем файлы основной ориентации
        copied_files = 0
        for file_path, ds in main_files:
            try:
                # Дополнительная проверка на согласованность
                slice_location = ds.get('SliceLocation', None)
                if slice_location is not None:
                    shutil.copy2(file_path, output_path / file_path.name)
                    copied_files += 1
            except Exception as e:
                logger.warning(f"Error copying {file_path}: {e}")
                continue
        
        logger.info(f"Copied {copied_files} DICOM files with consistent orientation")
        return copied_files >= 10  # Нужно минимум 10 срезов
        
    except Exception as e:
        logger.error(f"Failed to fix DICOM orientation: {e}")
        return False

def create_simple_dicom_test(dicom_dir: str, output_dir: str) -> bool:
    """
    Создает простой набор DICOM файлов для теста
    """
    try:
        dicom_path = Path(dicom_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Берем только первые 50 файлов
        dicom_files = list(dicom_path.glob("*.dcm"))[:50]
        
        if len(dicom_files) < 10:
            return False
            
        # Копируем файлы
        for file_path in dicom_files:
            try:
                shutil.copy2(file_path, output_path / file_path.name)
            except:
                continue
                
        logger.info(f"Created test set with {len(dicom_files)} files")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create test set: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python preprocess_dicom.py <input_dir> <output_dir> [--simple]")
        sys.exit(1)
        
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    use_simple = "--simple" in sys.argv
    
    if use_simple:
        success = create_simple_dicom_test(input_dir, output_dir)
    else:
        success = fix_dicom_orientation_issue(input_dir, output_dir)
    
    if success:
        print(f"✅ DICOM preprocessing successful: {output_dir}")
        sys.exit(0)
    else:
        print(f"❌ DICOM preprocessing failed")
        sys.exit(1)
