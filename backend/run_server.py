#!/usr/bin/env python3
"""
Финальный запускной скрипт для Laprascope API
"""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    try:
        print("🚀 Запуск Laprascope API...")
        print(f"📁 Project root: {project_root}")
        
        # Импортируем и настраиваем
        from app.main import app
        import uvicorn
        
        # Конфигурация запуска
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        debug = os.getenv("API_DEBUG", "false").lower() == "true"
        
        print(f"🌐 Host: {host}")
        print(f"🔌 Port: {port}")
        print(f"🐛 Debug: {debug}")
        print(f"📖 Docs: http://{host}:{port}/docs")
        print(f"❤️  Health: http://{host}:{port}/api/v1/health")
        
        # Запускаем сервер
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=debug,
            log_level="info" if not debug else "debug"
        )
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь что все зависимости установлены:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
