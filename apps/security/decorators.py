"""安全装饰器"""
from functools import wraps
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.core.exceptions import PermissionDenied
from .cache import CacheManager
from .logging import FileConverterLogger

cache_manager = CacheManager()
logger = FileConverterLogger()

def check_conversion_limits(view_func):
    """检查转换限制的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': _('Please login first')
            }, status=401)
            
        # 检查用户的转换配额
        user_quota = cache_manager.get_conversion_quota(request.user.id)
        if user_quota and user_quota['count'] >= user_quota['limit']:
            logger.log_security_event(
                'quota_exceeded',
                {'user_id': request.user.id},
                request.user
            )
            return JsonResponse({
                'status': 'error',
                'message': _('Conversion quota exceeded')
            }, status=429)
            
        return view_func(request, *args, **kwargs)
    return wrapper

def require_https(view_func):
    """要求HTTPS的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_secure():
            logger.log_security_event(
                'insecure_access',
                {'path': request.path},
                request.user if request.user.is_authenticated else None
            )
            return JsonResponse({
                'status': 'error',
                'message': _('HTTPS required')
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def check_ip_blacklist(view_func):
    """检查IP黑名单的装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        ip = request.META.get('REMOTE_ADDR')
        if cache_manager.is_ip_blacklisted(ip):
            logger.log_security_event(
                'blacklisted_ip_access',
                {'ip': ip},
                request.user if request.user.is_authenticated else None
            )
            raise PermissionDenied(_('Access denied'))
        return view_func(request, *args, **kwargs)
    return wrapper

def rate_limit(key_prefix, limit=100, period=3600):
    """速率限制装饰器"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 获取标识符
            if request.user.is_authenticated:
                identifier = f"{key_prefix}:user:{request.user.id}"
            else:
                identifier = f"{key_prefix}:ip:{request.META.get('REMOTE_ADDR')}"
            
            # 检查速率限制
            if not cache_manager.check_rate_limit(identifier):
                logger.log_security_event(
                    'rate_limit_exceeded',
                    {'identifier': identifier},
                    request.user if request.user.is_authenticated else None
                )
                return JsonResponse({
                    'status': 'error',
                    'message': _('Rate limit exceeded')
                }, status=429)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def log_access(action):
    """访问日志装饰器"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 记录访问信息
            logger.log_audit(
                action,
                request.user if request.user.is_authenticated else None,
                {
                    'path': request.path,
                    'method': request.method,
                    'ip': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT')
                }
            )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator 