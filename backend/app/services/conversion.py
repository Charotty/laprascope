"""
Модуль конвертации NIfTI в STL
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Добавляем путь к venv для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".venv" / "Lib" / "site-packages"))

try:
    import nibabel as nib
    import numpy as np
    from skimage.measure import marching_cubes
    import trimesh
except ImportError as e:
    logging.warning(f"Some conversion packages not available: {e}")

logger = logging.getLogger(__name__)

class ConversionError(Exception):
    """Исключения для ошибок конвертации"""
    pass

def convert_to_stl(nifti_path: str, stl_path: str, simplify: int = 50000) -> str:
    """
    Конвертирует NIfTI файл в STL mesh
    
    Args:
        nifti_path: путь к NIfTI файлу
        stl_path: путь для сохранения STL файла
        simplify: целевое количество треугольников для упрощения
        
    Returns:
        str: путь к созданному STL файлу
        
    Raises:
        ConversionError: если конвертация не удалась
    """
    logger.info(f"Converting {nifti_path} to {stl_path}")
    logger.info(f"Target simplification: {simplify} faces")
    
    try:
        # Проверяем, что входной файл существует
        if not os.path.exists(nifti_path):
            raise ConversionError(f"Input NIfTI file not found: {nifti_path}")
        
        # Загружаем NIfTI файл
        logger.info("Loading NIfTI file...")
        img = nib.load(nifti_path)
        data = img.get_fdata()
        
        logger.info(f"Input shape: {data.shape}")
        logger.info(f"Data type: {data.dtype}")
        logger.info(f"Data range: [{data.min()}, {data.max()}]")
        
        # Проверяем, что данные не пустые
        if data.max() == 0:
            raise ConversionError("Empty segmentation data - all voxels are zero")
        
        # Бинаризация - пороговое значение для сегментации
        threshold = 0.5  # Для бинарных масок
        binary_data = (data > threshold).astype(np.uint8)
        
        voxel_count = np.sum(binary_data)
        logger.info(f"Binary voxels: {voxel_count}")
        
        if voxel_count == 0:
            raise ConversionError("No voxels above threshold - empty segmentation")
        
        # Извлечение mesh с помощью marching cubes
        logger.info("Running marching cubes...")
        try:
            verts, faces, normals, values = marching_cubes(
                binary_data, 
                level=0.5, 
                spacing=img.header.get_zooms()[:3]
            )
            logger.info(f"Initial mesh: {len(verts)} vertices, {len(faces)} faces")
            
        except Exception as e:
            raise ConversionError(f"Marching cubes failed: {e}")
        
        if len(faces) == 0:
            raise ConversionError("No faces generated - empty mesh")
        
        # Создаем mesh
        logger.info("Creating mesh...")
        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        
        # Сглаживание
        logger.info("Applying Laplacian smoothing...")
        try:
            mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=5)
            logger.info(f"After smoothing: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        except Exception as e:
            logger.warning(f"Smoothing failed: {e}")
        
        # Упрощение до target_faces
        if len(mesh.faces) > simplify:
            logger.info(f"Simplifying mesh from {len(mesh.faces)} to {simplify} faces...")
            try:
                # Пробуем упростить
                simplified_mesh = mesh.simplify_quadric_decimation(simplify)
                if simplified_mesh.faces is not None and len(simplified_mesh.faces) > 0:
                    mesh = simplified_mesh
                    logger.info(f"After simplification: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
                else:
                    logger.warning(f"Simplification resulted in empty mesh, keeping original")
            except Exception as e:
                logger.warning(f"Simplification failed: {e}")
                # Продолжаем без упрощения
        
        # Проверяем mesh перед сохранением
        if mesh.faces is None or len(mesh.faces) == 0:
            raise ConversionError("Empty mesh after processing")
        
        # Создаем директорию для STL файла если нужно
        stl_dir = os.path.dirname(stl_path)
        if stl_dir:
            os.makedirs(stl_dir, exist_ok=True)
        
        # Сохранение STL
        logger.info(f"Saving STL to {stl_path}...")
        try:
            mesh.export(stl_path)
            
            # Проверяем размер файла
            file_size_mb = os.path.getsize(stl_path) / (1024 * 1024)
            logger.info(f"STL file size: {file_size_mb:.2f} MB")
            
            # Проверяем, что файл создан и не пустой
            if os.path.getsize(stl_path) == 0:
                raise ConversionError("STL file is empty")
            
            logger.info(f"✅ Successfully converted {nifti_path} to {stl_path}")
            logger.info(f"Final mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            
            return stl_path
            
        except Exception as e:
            raise ConversionError(f"Failed to save STL: {e}")
        
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Unexpected error during conversion: {e}")

def convert_organ_to_stl(job_id: str, organ_name: str, nifti_dir: str, stl_dir: str, simplify: int = 50000) -> Optional[str]:
    """
    Конвертирует NIfTI файл конкретного органа в STL
    
    Args:
        job_id: ID задачи
        organ_name: название органа ('kidney_left' или 'kidney_right')
        nifti_dir: директория с NIfTI файлами
        stl_dir: директория для сохранения STL файлов
        simplify: целевое количество треугольников
        
    Returns:
        Optional[str]: путь к STL файлу или None если конвертация не удалась
    """
    logger.info(f"Converting {organ_name} for job {job_id}")
    
    # Пути к файлам
    nifti_path = os.path.join(nifti_dir, f"{organ_name}.nii.gz")
    stl_path = os.path.join(stl_dir, f"{organ_name}.stl")
    
    try:
        return convert_to_stl(nifti_path, stl_path, simplify)
    except ConversionError as e:
        logger.error(f"Failed to convert {organ_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error converting {organ_name}: {e}")
        return None

if __name__ == "__main__":
    # Тестовый запуск
    logging.basicConfig(level=logging.INFO)
    
    test_nifti = "input/kidney_test.nii.gz"
    test_stl = "data/jobs/test_001/stl/kidney_test.stl"
    
    try:
        result = convert_to_stl(test_nifti, test_stl, simplify=50000)
        print(f"Test completed: {result}")
    except ConversionError as e:
        print(f"Test failed: {e}")
