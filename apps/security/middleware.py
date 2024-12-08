"""安全中间件"""
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import BlockedIP, AuditLog
import re

class SecurityMiddleware:
    """安全中间件"""
    def __init__(self, get_response):
        self.get_response = get_response
        # 编译白名单URL模式
        self.whitelist_patterns = [
            re.compile(pattern)
            for pattern in getattr(settings, 'SECURITY_URL_WHITELIST', [])
        ]

    def __call__(self, request):
        # 检查IP是否被封禁
        if self._check_ip_blocked(request):
            return HttpResponseForbidden('IP blocked')

        # 检查请求频率
        if not self._check_rate_limit(request):
            return HttpResponseForbidden('Rate limit exceeded')

        # 记录请求
        self._log_request(request)

        response = self.get_response(request)

        # 记录响应
        if response.status_code >= 400:
            self._log_error_response(request, response)

        return response

    def _check_ip_blocked(self, request):
        """检查IP是否被封禁"""
        ip = self._get_client_ip(request)
        
        # 检查白名单
        if self._is_whitelisted(request):
            return False
            
        return BlockedIP.objects.is_blocked(ip)

    def _check_rate_limit(self, request):
        """检查请求频率"""
        if self._is_whitelisted(request):
            return True
            
        ip = self._get_client_ip(request)
        path = request.path
        
        # 获取限制配置
        rate_limits = getattr(settings, 'SECURITY_RATE_LIMITS', {
            'default': '100/h',  # 默认限制
            'api': '1000/h',     # API限制
            'login': '5/m'       # 登录限制
        })
        
        # 确定使用哪个限制
        limit_key = 'default'
        for pattern, key in getattr(settings, 'SECURITY_RATE_PATTERNS', {}).items():
            if re.match(pattern, path):
                limit_key = key
                break
        
        limit = rate_limits.get(limit_key, rate_limits['default'])
        count, period = self._parse_rate_limit(limit)
        
        # 检查频率
        cache_key = f'rate_limit:{limit_key}:{ip}'
        current = cache.get(cache_key, 0)
        
        if current >= count:
            return False
            
        # 更新计数
        if current == 0:
            cache.set(cache_key, 1, timeout=period)
        else:
            cache.incr(cache_key)
            
        return True

    def _log_request(self, request):
        """记录请求"""
        if not self._should_log_request(request):
            return
            
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action_type='request',
            action_detail=f'Request to {request.path}',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            extra_data={
                'method': request.method,
                'path': request.path,
                'query': request.GET.dict(),
            }
        )

    def _log_error_response(self, request, response):
        """记录错误响应"""
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action_type='error',
            action_detail=f'Error {response.status_code} on {request.path}',
            severity='error' if response.status_code >= 500 else 'warning',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            extra_data={
                'status_code': response.status_code,
                'method': request.method,
                'path': request.path,
            }
        )

    def _get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _is_whitelisted(self, request):
        """检查是否在白名单中"""
        path = request.path
        return any(pattern.match(path) for pattern in self.whitelist_patterns)

    def _should_log_request(self, request):
        """检查是否应该记录请求"""
        # 不记录静态文件请求
        if request.path.startswith(('/static/', '/media/')):
            return False
            
        # 不记录健康检查请求
        if request.path == '/health/':
            return False
            
        return True

    def _parse_rate_limit(self, limit):
        """解析频率限制格式"""
        count, period = limit.split('/')
        count = int(count)
        
        if period == 's':
            seconds = 1
        elif period == 'm':
            seconds = 60
        elif period == 'h':
            seconds = 3600
        elif period == 'd':
            seconds = 86400
        else:
            seconds = 3600  # 默认1小时
            
        return count, seconds