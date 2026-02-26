"""
Улучшенная конфигурация логирования для AR Laparoscopy Project
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консольного вывода"""
    
    # ANSI escape codes для цветов
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Добавляем цвет только если вывод в консоль
        if hasattr(record, 'stream') and record.stream == 'console':
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Настраивает логирование с ротацией и уровнями
    
    Args:
        log_level: уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: директория для лог файлов
        max_file_size: максимальный размер одного лог файла
        backup_count: количество хранимых старых логов
        enable_console: включить вывод в консоль
        enable_file: включить вывод в файл
        log_format: кастомный формат логов
        
    Returns:
        logging.Logger: настроенный логгер
    """
    # Создаем директорию для логов
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Определяем формат логов
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Создаем корневой логгер
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Консольный обработчик
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Цветной форматтер для консоли
        console_formatter = ColoredFormatter(log_format)
        console_handler.setFormatter(console_formatter)
        
        # Добавляем атрибут для определения потока
        console_handler.stream = 'console'
        logger.addHandler(console_handler)
    
    # Файловый обработчик с ротацией
    if enable_file:
        # Имя файла с датой
        log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        log_file_path = log_path / log_filename
        
        # RotatingFileHandler с автоматической ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Стандартный форматтер для файла
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
        
        # Отдельный лог для ошибок
        error_log_filename = f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_log_path = log_path / error_log_filename
        
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(error_log_path),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
    
    # Настройка логгеров для сторонних библиотек
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("totalsegmentator").setLevel(logging.INFO)
    
    logger.info(f"Logging configured: level={log_level}, dir={log_dir}, console={enable_console}, file={enable_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер с унифицированной конфигурацией
    
    Args:
        name: имя логгера
        
    Returns:
        logging.Logger: настроенный логгер
    """
    return logging.getLogger(name)

def log_function_call(logger: logging.Logger, func_name: str, args: tuple = (), kwargs: dict = None):
    """
    Логирует вызов функции (для отладки)
    
    Args:
        logger: логгер
        func_name: имя функции
        args: позиционные аргументы
        kwargs: именованные аргументы
    """
    if logger.isEnabledFor(logging.DEBUG):
        args_str = ", ".join(str(arg) for arg in args)
        kwargs_str = ", ".join(f"{k}={v}" for k, v in (kwargs or {}).items())
        
        all_args = []
        if args_str:
            all_args.append(args_str)
        if kwargs_str:
            all_args.append(kwargs_str)
        
        full_args = ", ".join(all_args)
        logger.debug(f"Calling {func_name}({full_args})")

def log_performance(logger: logging.Logger, operation: str, duration: float, details: dict = None):
    """
    Логирует производительность операции
    
    Args:
        logger: логгер
        operation: название операции
        duration: длительность в секундах
        details: дополнительные детали
    """
    details_str = ""
    if details:
        details_str = " | " + " | ".join(f"{k}={v}" for k, v in details.items())
    
    logger.info(f"Performance: {operation} completed in {duration:.2f}s{details_str}")

# Контекстный менеджер для измерения времени
import time
from contextlib import contextmanager

@contextmanager
def measure_time(logger: logging.Logger, operation: str, details: dict = None):
    """
    Измеряет время выполнения операции и логирует результат
    
    Usage:
        with measure_time(logger, "segmentation", {"job_id": job_id}):
            # ... код операции ...
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        log_performance(logger, operation, duration, details)
