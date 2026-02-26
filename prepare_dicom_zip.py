#!/usr/bin/env python3
"""
Скрипт для подготовки ZIP архивов из DICOM файлов для загрузки на сервер
"""
import os
import sys
import zipfile
import argparse
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_dicom_files(base_dir: Path) -> dict:
    """Находит все DICOM исследования в директории"""
    studies = {}
    
    # Рекурсивный поиск всех файлов
    for file_path in base_dir.rglob("*"):
        if file_path.is_file():
            # Пропускаем служебные файлы
            if file_path.name in ['DICOMDIR', 'Autorun.inf', 'amImageViewer.exe', 
                               'Images.cds', 'Protocols.cds', 'lex_img.cds']:
                continue
            
            # Проверяем что это DICOM файл (по размеру ~527KB и без расширения)
            if (file_path.stat().st_size > 400000 and 
                file_path.stat().st_size < 600000 and
                not file_path.suffix):
                
                # Определяем исследование по родительским директориям
                parts = file_path.parts
                if len(parts) >= 3:
                    patient_name = parts[-3]  # Мовсесян Ярика 08.09.2024 Натив
                    study_date = parts[-2]     # 24090213
                    
                    study_key = f"{patient_name}_{study_date}"
                    
                    if study_key not in studies:
                        studies[study_key] = {
                            'patient': patient_name,
                            'date': study_date,
                            'files': []
                        }
                    
                    studies[study_key]['files'].append(file_path)
    
    return studies

def create_study_zip(study_info: dict, output_dir: Path) -> Path:
    """Создает ZIP архив для одного исследования"""
    patient_name = study_info['patient']
    study_date = study_info['date']
    files = study_info['files']
    
    # Создаем имя файла
    safe_patient = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    zip_name = f"{safe_patient}_{study_date}.zip"
    zip_path = output_dir / zip_name
    
    logger.info(f"Creating ZIP: {zip_name}")
    logger.info(f"Patient: {patient_name}")
    logger.info(f"Study: {study_date}")
    logger.info(f"Files: {len(files)}")
    
    # Создаем ZIP архив
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            # Добавляем файл с расширением .dcm
            arcname = f"{study_date}/{file_path.name}.dcm"
            zipf.write(file_path, arcname)
            logger.debug(f"Added: {file_path} -> {arcname}")
    
    logger.info(f"Created ZIP: {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
    return zip_path

def main():
    parser = argparse.ArgumentParser(description='Подготовка ZIP архивов DICOM для загрузки')
    parser.add_argument('input_dir', help='Директория с DICOM файлами')
    parser.add_argument('output_dir', help='Директория для сохранения ZIP архивов')
    parser.add_argument('--patient', help='ФИО пациента (опционально)')
    parser.add_argument('--list', action='store_true', help='Только список исследований')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Создаем выходную директорию
    output_dir.mkdir(exist_ok=True)
    
    # Находим все исследования
    studies = find_dicom_files(input_dir)
    
    if not studies:
        logger.error("No DICOM studies found")
        sys.exit(1)
    
    logger.info(f"Found {len(studies)} studies:")
    for study_key, study_info in studies.items():
        logger.info(f"  - {study_key}: {len(study_info['files'])} files")
    
    if args.list:
        return
    
    # Фильтруем по пациенту если указан
    if args.patient:
        filtered_studies = {k: v for k, v in studies.items() 
                         if args.patient.lower() in v['patient'].lower()}
        studies = filtered_studies
        
        if not studies:
            logger.error(f"No studies found for patient: {args.patient}")
            sys.exit(1)
    
    # Создаем ZIP архивы
    created_zips = []
    for study_key, study_info in studies.items():
        try:
            zip_path = create_study_zip(study_info, output_dir)
            created_zips.append(zip_path)
        except Exception as e:
            logger.error(f"Failed to create ZIP for {study_key}: {e}")
    
    logger.info(f"Created {len(created_zips)} ZIP archives:")
    for zip_path in created_zips:
        logger.info(f"  - {zip_path}")

if __name__ == "__main__":
    main()
