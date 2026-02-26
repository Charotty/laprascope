#!/usr/bin/env python3
"""
Альтернативный метод конвертации DICOM в NIfTI с использованием dcm2niix
"""
import os
import subprocess
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def convert_dicom_with_dcm2niix(dicom_dir: str, output_dir: str) -> bool:
    """
    Конвертирует DICOM в NIfTI с использованием dcm2niix
    """
    try:
        # Проверяем наличие dcm2niix
        try:
            subprocess.run(['dcm2niix', '-h'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("dcm2niix not found. Installing...")
            # Устанавливаем dcm2niix
            subprocess.run(['apt', 'update'], check=True)
            subprocess.run(['apt', 'install', '-y', 'dcm2niix'], check=True)
        
        dicom_path = Path(dicom_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Конвертируем с dcm2niix
        cmd = [
            'dcm2niix',
            '-m', 'y',  # Создавать 3D объем
            '-z', 'y',  # Сжимать
            '-x', 'y',  # Игнорировать производные
            '-f', 'converted',  # Имя файла
            '-o', str(output_path),  # Выходная директория
            str(dicom_path)  # Входная директория
        ]
        
        logger.info(f"Running dcm2niix: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Ищем созданный NIfTI файл
            nifti_files = list(output_path.glob("converted.nii.gz"))
            if nifti_files:
                logger.info(f"Successfully converted with dcm2niix: {nifti_files[0]}")
                return True
            else:
                logger.error("No NIfTI file created by dcm2niix")
                return False
        else:
            logger.error(f"dcm2niix failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("dcm2niix conversion timed out")
        return False
    except Exception as e:
        logger.error(f"dcm2niix conversion failed: {e}")
        return False

def create_fallback_nifti(dicom_dir: str, output_dir: str) -> bool:
    """
    Создает fallback NIfTI файл из первых DICOM срезов
    """
    try:
        import pydicom
        import numpy as np
        import nibabel as nib
        
        dicom_path = Path(dicom_dir)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Получаем первые 20 DICOM файлов
        dicom_files = list(dicom_path.glob("*.dcm"))[:20]
        
        if len(dicom_files) < 5:
            logger.error(f"Too few DICOM files: {len(dicom_files)}")
            return False
        
        # Читаем и сортируем файлы
        slices = []
        for file_path in dicom_files:
            try:
                ds = pydicom.dcmread(str(file_path))
                slices.append((ds.get('InstanceNumber', 0), ds))
            except Exception as e:
                logger.warning(f"Cannot read {file_path}: {e}")
                continue
        
        if len(slices) < 5:
            logger.error(f"Too few valid DICOM slices: {len(slices)}")
            return False
        
        # Сортируем по номеру среза
        slices.sort(key=lambda x: x[0])
        
        # Создаем 3D объем
        first_slice = slices[0][1]
        pixel_data = first_slice.pixel_array
        
        # Инициализируем 3D массив
        volume_shape = (len(slices), pixel_data.shape[0], pixel_data.shape[1])
        volume = np.zeros(volume_shape, dtype=pixel_data.dtype)
        
        # Заполняем объем
        for i, (_, ds) in enumerate(slices):
            volume[i] = ds.pixel_array
        
        # Создаем NIfTI
        affine = np.eye(4)
        nifti_img = nib.Nifti1Image(volume, affine)
        
        # Сохраняем
        output_file = output_path / "fallback.nii.gz"
        nib.save(nifti_img, str(output_file))
        
        logger.info(f"Created fallback NIfTI: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create fallback NIfTI: {e}")
        return False
