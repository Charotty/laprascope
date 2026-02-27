#!/usr/bin/env python3
"""
Максимально простой запуск сервера с очисткой зависших процессов
"""
import sys
import os
import signal
import subprocess
from pathlib import Path

# Правильный путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def cleanup_hanging_processes():
    """Очищает зависшие процессы"""
    print("🧹 Очистка зависших процессов...")
    
    try:
        # Убиваем зависшие процессы
        subprocess.run(["pkill", "-f", "totalsegmentator"], capture_output=True)
        subprocess.run(["pkill", "-f", "python.*segmentation"], capture_output=True)
        subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
        
        # Очищаем временные файлы
        subprocess.run(["rm", "-rf", "/tmp/totalsegmentator_*"], capture_output=True)
        
        print("✅ Очистка завершена")
    except Exception as e:
        print(f"⚠️ Ошибка очистки: {e}")

def signal_handler(sig, frame):
    """Обработчик сигнала для graceful shutdown"""
    print("\n🛑 Получен сигнал завершения...")
    cleanup_hanging_processes()
    sys.exit(0)

# Устанавливаем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("🚀 Запуск Laprascope API...")

# Сначала очищаем зависшие процессы
cleanup_hanging_processes()

try:
    # Импортируем и запускаем
    from app.main import app
    import uvicorn
    
    print("✅ Импорты успешны!")
    print("🌐 Сервер запускается на http://0.0.0.0:8000")
    print("📖 Документация: http://0.0.0.0:8000/docs")
    print("❤️ Health check: http://0.0.0.0:8000/api/v1/health")
    
    # Запускаем с базовыми настройками
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        timeout_keep_alive=300,  # 5 минут таймаут
        workers=1  # Один воркер для избежания проблем
    )
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    cleanup_hanging_processes()
