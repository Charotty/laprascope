#!/usr/bin/env python3
"""
Патч для исправления проблем с PyTorch 2.6 и totalsegmentator
"""
import torch
import numpy as np
import logging

logger = logging.getLogger(__name__)

def patch_pytorch_for_totalsegmentator():
    """
    Применяет патчи для совместимости с PyTorch 2.6
    """
    try:
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
        logger.info(f"📋 Added {len(numpy_globals)} NumPy globals and {len(torch_globals)} PyTorch globals")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply PyTorch compatibility patch: {e}")
        return False

def patch_torch_load_for_legacy_models():
    """
    Создает безопасную версию torch.load для старых моделей
    """
    original_torch_load = torch.load
    
    def safe_torch_load(f, *args, **kwargs):
        """
        Безопасная загрузка моделей с fallback на weights_only=False
        """
        try:
            # Сначала пробуем с weights_only=True (безопасно)
            return original_torch_load(f, *args, weights_only=True, **kwargs)
        except Exception as e:
            if "weights_only" in str(e).lower() or "unsupported global" in str(e).lower():
                logger.warning(f"⚠️ Safe load failed, trying with weights_only=False: {e}")
                # Fallback на старый режим (только если доверяем источнику)
                return original_torch_load(f, *args, weights_only=False, **kwargs)
            else:
                # Другая ошибка, пробуем оригинальный метод
                return original_torch_load(f, *args, **kwargs)
    
    # Заменяем torch.load
    torch.load = safe_torch_load
    logger.info("🔧 torch.load patched for legacy model compatibility")
    
    return original_torch_load

def apply_all_patches():
    """
    Применяет все патчи для совместимости
    """
    logger.info("🚀 Applying PyTorch 2.6 compatibility patches...")
    
    success = True
    
    # Патч для безопасных глобальных переменных
    if not patch_pytorch_for_totalsegmentator():
        success = False
    
    # Патч для torch.load
    try:
        patch_torch_load_for_legacy_models()
    except Exception as e:
        logger.error(f"❌ Failed to patch torch.load: {e}")
        success = False
    
    if success:
        logger.info("✅ All PyTorch compatibility patches applied successfully")
    else:
        logger.error("❌ Some patches failed to apply")
    
    return success

# Автоматически применяем патчи при импорте
if torch.__version__.startswith('2.'):
    apply_all_patches()
