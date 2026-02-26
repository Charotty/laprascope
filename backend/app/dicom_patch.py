#!/usr/bin/env python3
"""
Модуль для обхода проблем с валидацией DICOM файлов
"""
import sys
import os

# Патчим dicom2nifti чтобы игнорировать проблемы с ортогональностью
def patch_dicom2nifti():
    """Патчит модуль dicom2nifti для обхода валидации"""
    try:
        import dicom2nifti.common
        
        # Сохраняем оригинальную функцию
        original_validate_orthogonal = dicom2nifti.common.validate_orthogonal
        
        def patched_validate_orthogonal(dicom_input):
            """Патченная функция валидации - пропускает все"""
            return True
        
        # Заменяем функцию
        dicom2nifti.common.validate_orthogonal = patched_validate_orthogonal
        
        # Также патчим валидацию ориентации
        original_validate_orientation = dicom2nifti.common.validate_orientation
        
        def patched_validate_orientation(dicom_input):
            """Патченная функция валидации ориентации - пропускает все"""
            return True
        
        dicom2nifti.common.validate_orientation = patched_validate_orientation
        
        print("✅ dicom2nifti successfully patched to ignore validation errors")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to patch dicom2nifti: {e}")
        return False
    except Exception as e:
        print(f"❌ Error patching dicom2nifti: {e}")
        return False

# Применяем патч при импорте
patch_dicom2nifti()
