"""
Единый модуль обработки ошибок для AR Laparoscopy Project
"""
import logging
import traceback
from typing import Optional, Dict, Any
from enum import Enum

class ErrorType(Enum):
    """Типы ошибок"""
    VALIDATION = "validation_error"
    PROCESSING = "processing_error"
    NETWORK = "network_error"
    FILE_SYSTEM = "file_system_error"
    MEMORY = "memory_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    RATE_LIMIT = "rate_limit_error"
    TIMEOUT = "timeout_error"
    UNKNOWN = "unknown_error"

class ErrorSeverity(Enum):
    """Уровни критичности ошибок"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class APIError(Exception):
    """Базовый класс для API ошибок"""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.original_error = original_error
        
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует ошибку в словарь для API ответа"""
        return {
            "error": {
                "type": self.error_type.value,
                "message": self.message,
                "severity": self.severity.value,
                "details": self.details
            }
        }
    
    def log(self, logger: logging.Logger, context: Optional[str] = None):
        """Логирует ошибку с учётом контекста и критичности"""
        log_message = f"{self.message}"
        if context:
            log_message = f"{context}: {log_message}"
        
        if self.original_error:
            log_message += f" (Original: {type(self.original_error).__name__}: {self.original_error})"
        
        # Выбираем уровень логирования на основе критичности
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Добавляем traceback для критичных ошибок
        if self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.debug(traceback.format_exc())

# Удобные функции для создания типовых ошибок
def validation_error(message: str, details: Optional[Dict] = None) -> APIError:
    """Создает ошибку валидации"""
    return APIError(
        message=message,
        error_type=ErrorType.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        details=details
    )

def processing_error(message: str, original_error: Optional[Exception] = None, details: Optional[Dict] = None) -> APIError:
    """Создает ошибку обработки"""
    return APIError(
        message=message,
        error_type=ErrorType.PROCESSING,
        severity=ErrorSeverity.HIGH,
        original_error=original_error,
        details=details
    )

def file_system_error(message: str, original_error: Optional[Exception] = None, details: Optional[Dict] = None) -> APIError:
    """Создает ошибку файловой системы"""
    return APIError(
        message=message,
        error_type=ErrorType.FILE_SYSTEM,
        severity=ErrorSeverity.MEDIUM,
        original_error=original_error,
        details=details
    )

def memory_error(message: str, original_error: Optional[Exception] = None, details: Optional[Dict] = None) -> APIError:
    """Создает ошибку памяти"""
    return APIError(
        message=message,
        error_type=ErrorType.MEMORY,
        severity=ErrorSeverity.CRITICAL,
        original_error=original_error,
        details=details
    )

def network_error(message: str, original_error: Optional[Exception] = None, details: Optional[Dict] = None) -> APIError:
    """Создает сетевую ошибку"""
    return APIError(
        message=message,
        error_type=ErrorType.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        original_error=original_error,
        details=details
    )

def timeout_error(message: str, original_error: Optional[Exception] = None, details: Optional[Dict] = None) -> APIError:
    """Создает ошибку таймаута"""
    return APIError(
        message=message,
        error_type=ErrorType.TIMEOUT,
        severity=ErrorSeverity.MEDIUM,
        original_error=original_error,
        details=details
    )

def handle_exception(
    logger: logging.Logger,
    exception: Exception,
    context: Optional[str] = None,
    default_message: str = "An unexpected error occurred"
) -> APIError:
    """
    Унифицированная обработка исключений
    
    Args:
        logger: логгер для записи ошибки
        exception: исключение для обработки
        context: контекст возникновения ошибки
        default_message: сообщение по умолчанию
        
    Returns:
        APIError: стандартизированная ошибка
    """
    # Определяем тип и критичность на основе исключения
    if isinstance(exception, (FileNotFoundError, PermissionError, OSError)):
        return file_system_error(
            message=str(exception) or default_message,
            original_error=exception,
            details={"context": context}
        )
    elif isinstance(exception, MemoryError):
        return memory_error(
            message=str(exception) or default_message,
            original_error=exception,
            details={"context": context}
        )
    elif isinstance(exception, (ConnectionError, TimeoutError)):
        return network_error(
            message=str(exception) or default_message,
            original_error=exception,
            details={"context": context}
        )
    elif isinstance(exception, ValueError):
        return validation_error(
            message=str(exception) or default_message,
            details={"context": context}
        )
    else:
        return APIError(
            message=str(exception) or default_message,
            error_type=ErrorType.UNKNOWN,
            severity=ErrorSeverity.HIGH,
            original_error=exception,
            details={"context": context, "exception_type": type(exception).__name__}
        )
