"""错误处理"""
from functools import wraps
from django.http import JsonResponse
from django.utils.translation import gettext as _
from .logging import FileConverterLogger

logger = FileConverterLogger()

class SecurityError(Exception):
    """安全相关错误的基类"""
    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

class FileValidationError(SecurityError):
    """文件验证错误"""
    pass

class QuotaExceededError(SecurityError):
    """配额超限错误"""
    pass

class RateLimitExceededError(SecurityError):
    """速率限制错误"""
    pass

class BlacklistedError(SecurityError):
    """黑名单错误"""
    pass

class ConversionError(SecurityError):
    """转换错误"""
    pass

def handle_security_errors(view_func):
    """处理安全相关错误的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except FileValidationError as e:
            logger.log_error('file_validation_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'validation_error',
                'message': str(e),
                'details': e.details
            }, status=400)
        except QuotaExceededError as e:
            logger.log_error('quota_exceeded', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'quota_exceeded',
                'message': str(e),
                'details': e.details
            }, status=429)
        except RateLimitExceededError as e:
            logger.log_error('rate_limit_exceeded', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'rate_limit_exceeded',
                'message': str(e),
                'details': e.details
            }, status=429)
        except BlacklistedError as e:
            logger.log_error('blacklisted', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'blacklisted',
                'message': str(e),
                'details': e.details
            }, status=403)
        except ConversionError as e:
            logger.log_error('conversion_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'conversion_error',
                'message': str(e),
                'details': e.details
            }, status=400)
        except SecurityError as e:
            logger.log_error('security_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'security_error',
                'message': str(e),
                'details': e.details
            }, status=400)
        except Exception as e:
            logger.log_error('unexpected_error', str(e))
            return JsonResponse({
                'status': 'error',
                'code': 'unexpected_error',
                'message': _('An unexpected error occurred')
            }, status=500)
    return wrapper

def handle_conversion_errors(view_func):
    """处理转换错误的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ConversionError as e:
            logger.log_error('conversion_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'code': e.code or 'conversion_error',
                'message': str(e),
                'details': e.details
            }, status=400)
        except Exception as e:
            logger.log_error('conversion_unexpected_error', str(e))
            return JsonResponse({
                'status': 'error',
                'code': 'conversion_error',
                'message': _('Conversion failed: {error}').format(error=str(e))
            }, status=500)
    return wrapper

def api_error_handler(view_func):
    """API错误处理装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            error_data = {
                'status': 'error',
                'code': getattr(e, 'code', 'api_error'),
                'message': str(e)
            }
            
            if hasattr(e, 'details'):
                error_data['details'] = e.details
                
            logger.log_error('api_error', str(e), getattr(e, 'details', None))
            
            return JsonResponse(error_data, status=getattr(e, 'status_code', 400))
    return wrapper 