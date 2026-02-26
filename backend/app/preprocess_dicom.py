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
    Исправляет DICOM файлы с проблемами ориентации и пропущенными срезами
    """
    try:
        dicom_path = Path(dicom_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Получаем все DICOM файлы с метаданными
        dicom_files = []
        for file_path in dicom_path.glob("*.dcm"):
            try:
                ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
                
                # Получаем важные метаданные
                metadata = {
                    'file_path': file_path,
                    'slice_location': float(ds.get('SliceLocation', 0)),
                    'instance_number': int(ds.get('InstanceNumber', 0)),
                    'series_number': str(ds.get('SeriesNumber', '1')),
                    'orientation': ds.get('ImageOrientationPatient', None),
                    'study_instance_uid': str(ds.get('StudyInstanceUID', '')),
                    'series_instance_uid': str(ds.get('SeriesInstanceUID', ''))
                }
                dicom_files.append(metadata)
                
            except Exception as e:
                logger.warning(f"Cannot read {file_path}: {e}")
                continue
                
        if len(dicom_files) < 10:
            logger.warning(f"Too few DICOM files: {len(dicom_files)}")
            return False
            
        # Группируем по сериям
        series_groups = {}
        for dicom_file in dicom_files:
            series_uid = dicom_file['series_instance_uid']
            if series_uid not in series_groups:
                series_groups[series_uid] = []
            series_groups[series_uid].append(dicom_file)
        
        logger.info(f"Found {len(series_groups)} DICOM series")
        
        # Находим самую большую и полную серию
        best_series = None
        best_score = 0
        
        for series_uid, files in series_groups.items():
            # Сортируем по номеру среза
            files.sort(key=lambda x: x['instance_number'])
            
            # Проверяем последовательность срезов
            slice_numbers = [f['instance_number'] for f in files]
            expected_numbers = list(range(min(slice_numbers), max(slice_numbers) + 1))
            
            # Вычисляем полноту серии
            completeness = len(set(slice_numbers) & set(expected_numbers)) / len(expected_numbers)
            
            # Вычисляем согласованность ориентации
            orientations = [f['orientation'] for f in files if f['orientation'] is not None]
            orientation_consistency = len(set(str(o) for o in orientations)) / len(orientations) if orientations else 0
            
            # Общий счет качества
            score = len(files) * completeness * (1 - orientation_consistency)
            
            logger.info(f"Series {series_uid}: {len(files)} files, completeness: {completeness:.2f}, orientation_consistency: {orientation_consistency:.2f}, score: {score:.1f}")
            
            if score > best_score:
                best_score = score
                best_series = series_uid
        
        if best_series is None:
            logger.error("No valid DICOM series found")
            return False
            
        best_files = series_groups[best_series]
        logger.info(f"Selected best series: {best_series} with {len(best_files)} files")
        
        # Проверяем минимальное количество срезов
        if len(best_files) < 20:
            logger.warning(f"Best series has too few slices: {len(best_files)}")
            # Все равно пробуем, но с предупреждением
        
        # Копируем файлы лучшей серии
        copied_files = 0
        for dicom_file in best_files:
            try:
                file_path = dicom_file['file_path']
                shutil.copy2(file_path, output_path / file_path.name)
                copied_files += 1
            except Exception as e:
                logger.warning(f"Error copying {file_path}: {e}")
                continue
        
        logger.info(f"Copied {copied_files} DICOM files from best series")
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
