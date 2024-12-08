"""自定义异常类"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class FileConversionError(Exception):
    """文件转换错误基类"""
    pass

class FileValidationError(ValidationError):
    """文件验证错误"""
    pass

class QuotaExceededError(ValidationError):
    """配额超限错误"""
    pass

class RateLimitExceededError(ValidationError):
    """速率限制错误"""
    pass

class SecurityError(ValidationError):
    """安全相关错误"""
    pass

class ConversionProcessError(FileConversionError):
    """转换过程错误"""
    pass

class TaskStateError(FileConversionError):
    """任务状态错误"""
    pass

class TaskNotFoundError(FileConversionError):
    """任务不存在错误"""
    pass

class InvalidOperationError(FileConversionError):
    """无效操作错误"""
    pass

class ConcurrencyError(FileConversionError):
    """并发处理错误"""
    pass

class LockAcquisitionError(ConcurrencyError):
    """锁获取错误"""
    pass

class DeadlockError(ConcurrencyError):
    """死锁错误"""
    pass 