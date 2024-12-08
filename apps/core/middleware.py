"""错误处理中间件"""
from django.shortcuts import render
from django.http import HttpResponseServerError
from django.utils.deprecation import MiddlewareMixin
import logging
import uuid

logger = logging.getLogger('apps.core')

class ErrorHandlerMiddleware(MiddlewareMixin):
    """错误处理中间件"""
    
    def process_exception(self, request, exception):
        """处理异常"""
        # 生成错误ID
        error_id = str(uuid.uuid4())
        
        # 记录错误日志
        logger.error(
            f"Error ID: {error_id}\nURL: {request.path}\nError: {str(exception)}",
            exc_info=True,
            extra={
                'error_id': error_id,
                'request': request,
                'user_id': request.user.id if request.user.is_authenticated else None
            }
        )
        
        # 返回500错误页面
        return HttpResponseServerError(
            render(
                request,
                'errors/500.html',
                {'error_id': error_id}
            )
        )

class MaintenanceModeMiddleware(MiddlewareMixin):
    """维护模式中间件"""
    
    def process_request(self, request):
        """处理请求"""
        from django.conf import settings
        
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # 允许管理员访问
            if request.user.is_staff:
                return None
                
            # 允许访问静态文件和维护页面
            if any(path in request.path for path in ['/static/', '/media/', '/maintenance/']):
                return None
                
            # 返回维护页面
            return render(
                request,
                'errors/maintenance.html',
                {
                    'maintenance_message': getattr(settings, 'MAINTENANCE_MESSAGE', None),
                    'completion_time': getattr(settings, 'MAINTENANCE_END_TIME', None)
                }
            )
        return None 