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
    from skimage.measure import marching_cubes
    import trimesh
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def nifti_to_stl(nifti_path, stl_path, target_faces=50000):
        """
        Конвертирует NIfTI файл в STL mesh
        
        Args:
            nifti_path: путь к NIfTI файлу
            stl_path: путь для сохранения STL файла
            target_faces: целевое количество треугольников в mesh
        """
        logger.info(f"Converting {nifti_path} to {stl_path}")
        start_time = time.time()
        
        # Загружаем NIfTI файл
        img = nib.load(nifti_path)
        data = img.get_fdata()
        
        logger.info(f"Input shape: {data.shape}")
        logger.info(f"Data type: {data.dtype}")
        logger.info(f"Data range: [{data.min()}, {data.max()}]")
        
        # Бинаризация - пороговое значение для сегментации
        threshold = 0.5  # Для бинарных масок
        binary_data = (data > threshold).astype(np.uint8)
        
        logger.info(f"Binary voxels: {np.sum(binary_data)}")
        
        # Извлечение mesh с помощью marching cubes
        try:
            verts, faces, normals, values = marching_cubes(
                binary_data, 
                level=0.5, 
                spacing=img.header.get_zooms()[:3]
            )
            logger.info(f"Initial mesh: {len(verts)} vertices, {len(faces)} faces")
            
        except Exception as e:
            logger.error(f"Marching cubes failed: {e}")
            return False
        
        # Создаем mesh
        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        
        # Сглаживание
        logger.info("Applying Laplacian smoothing...")
        try:
            mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=5)
            logger.info(f"After smoothing: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        except Exception as e:
            logger.warning(f"Smoothing failed: {e}")
        
        # Упрощение до target_faces
        if len(mesh.faces) > target_faces:
            logger.info(f"Simplifying mesh to {target_faces} faces...")
            try:
                mesh = mesh.simplify_quadric_decimation(target_faces)
                logger.info(f"After simplification: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            except Exception as e:
                logger.warning(f"Simplification failed: {e}")
        
        # Сохранение STL
        try:
            mesh.export(stl_path)
            file_size_mb = os.path.getsize(stl_path) / (1024 * 1024)
            logger.info(f"Saved STL to {stl_path}")
            logger.info(f"File size: {file_size_mb:.2f} MB")
            
            end_time = time.time()
            logger.info(f"Conversion time: {end_time - start_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save STL: {e}")
            return False
    
    def test_conversion():
        """Тестовая конвертация почек"""
        input_files = [
            "input/kidney_test.nii.gz",  # Используем реальный файл из kits23
            "output/kidney_left.nii.gz",
            "output/kidney_right.nii.gz"
        ]
        
        for input_file in input_files:
            if os.path.exists(input_file):
                output_file = input_file.replace(".nii.gz", ".stl")
                success = nifti_to_stl(input_file, output_file, target_faces=50000)
                
                if success:
                    logger.info(f"✅ Successfully converted {input_file} to {output_file}")
                else:
                    logger.error(f"❌ Failed to convert {input_file}")
            else:
                logger.warning(f"⚠️  File not found: {input_file}")
    
    if __name__ == "__main__":
        test_conversion()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure required packages are installed")
