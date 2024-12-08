"""错误处理装饰器"""
from functools import wraps
from django.http import JsonResponse
from django.utils.translation import gettext as _
from .exceptions import *
import logging

logger = logging.getLogger('apps.core')

def handle_conversion_errors(view_func):
    """处理转换错误的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except FileValidationError as e:
            logger.warning(f"File validation error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
        except QuotaExceededError as e:
            logger.warning(f"Quota exceeded: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=429)
        except RateLimitExceededError as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=429)
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': _("Security check failed")
            }, status=403)
        except ConversionProcessError as e:
            logger.error(f"Conversion error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)
        except TaskStateError as e:
            logger.warning(f"Task state error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
        except TaskNotFoundError as e:
            logger.warning(f"Task not found: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=404)
        except InvalidOperationError as e:
            logger.warning(f"Invalid operation: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
        except ConcurrencyError as e:
            logger.error(f"Concurrency error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=409)
        except Exception as e:
            logger.exception("Unexpected error")
            return JsonResponse({
                'status': 'error',
                'error': _("An unexpected error occurred")
            }, status=500)
    return wrapper 