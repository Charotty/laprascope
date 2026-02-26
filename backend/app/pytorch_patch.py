#!/usr/bin/env python3
"""
Простой патч для исправления проблем с PyTorch 2.6 и totalsegmentator
"""
import os
import torch
import numpy as np
import logging

logger = logging.getLogger(__name__)

def patch_pytorch_for_totalsegmentator():
    """
    Применяет патчи для совместимости с PyTorch 2.6
    """
    try:
        # Устанавливаем переменные окружения для PyTorch
        os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD'] = '1'
        
        # Добавляем numpy типы в безопасные глобальные переменные
        numpy_globals = [
            (np.core.multiarray._reconstruct, "numpy.core.multiarray._reconstruct"),
            np.ndarray,
            np.dtype,
            (np.core.multiarray.scalar, "numpy.core.multiarray.scalar"),
            np.float64,
            np.float32,
            np.int64,
            np.int32,
        ]
        
        # Добавляем torch типы
        torch_globals = [
            torch.optim.Adam,
            torch.optim.SGD,
            torch.optim.lr_scheduler.StepLR,
        ]
        
        # Применяем безопасные глобальные переменные
        torch.serialization.add_safe_globals(numpy_globals + torch_globals)
        
        logger.info("✅ PyTorch 2.6 compatibility patch applied successfully")
        logger.info("🔧 TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 set")
        logger.info(f"📋 Added {len(numpy_globals)} NumPy globals and {len(torch_globals)} PyTorch globals")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply PyTorch compatibility patch: {e}")
        return False

def apply_all_patches():
    """
    Применяет все патчи для совместимости
    """
    logger.info("🚀 Applying PyTorch 2.6 compatibility patches...")
    
    success = True
    
    # Патч для безопасных глобальных переменных и переменных окружения
    if not patch_pytorch_for_totalsegmentator():
        success = False
    
    if success:
        logger.info("✅ All PyTorch compatibility patches applied successfully")
    else:
        logger.error("❌ Some patches failed to apply")
    
    return success

# Автоматически применяем патчи при импорте
if torch.__version__.startswith('2.'):
    apply_all_patches()
