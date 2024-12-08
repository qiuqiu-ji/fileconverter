"""错误页面视图"""
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import requires_csrf_token
from django.http import JsonResponse
import logging

logger = logging.getLogger('apps.core')

@requires_csrf_token
def error_403(request, exception=None, template_name='errors/403.html'):
    """403权限错误处理"""
    context = {
        'title': _('Access Denied'),
        'reason': str(exception) if exception else None
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'code': 403,
            'message': context['reason'] or _('You do not have permission to access this resource.')
        }, status=403)
        
    return render(request, template_name, context, status=403)

@requires_csrf_token
def error_404(request, exception=None, template_name='errors/404.html'):
    """404页面不存在错误处理"""
    context = {
        'title': _('Page Not Found'),
        'request_path': request.path,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'code': 404,
            'message': _('The requested resource was not found.')
        }, status=404)
        
    return render(request, template_name, context, status=404)

@requires_csrf_token
def error_500(request, template_name='errors/500.html'):
    """500服务器错误处理"""
    error_id = getattr(request, 'error_id', None)
    
    context = {
        'title': _('Server Error'),
        'error_id': error_id
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'code': 500,
            'message': _('An unexpected error occurred.'),
            'error_id': error_id
        }, status=500)
        
    return render(request, template_name, context, status=500)

def maintenance(request, template_name='errors/maintenance.html'):
    """维护页面"""
    from django.conf import settings
    
    context = {
        'title': _('System Maintenance'),
        'maintenance_message': getattr(settings, 'MAINTENANCE_MESSAGE', None),
        'start_time': getattr(settings, 'MAINTENANCE_START_TIME', None),
        'duration': getattr(settings, 'MAINTENANCE_DURATION', None),
        'completion_time': getattr(settings, 'MAINTENANCE_END_TIME', None)
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'maintenance',
            'message': context['maintenance_message'],
            'completion_time': context['completion_time']
        }, status=503)
        
    return render(request, template_name, context, status=503)

def error_test(request):
    """错误测试视图（仅在DEBUG模式下可用）"""
    from django.conf import settings
    
    if not settings.DEBUG:
        raise Http404
        
    error_type = request.GET.get('type', '404')
    
    if error_type == '403':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Test 403 error")
    elif error_type == '404':
        from django.http import Http404
        raise Http404("Test 404 error")
    elif error_type == '500':
        raise Exception("Test 500 error")
    else:
        return JsonResponse({'message': 'Invalid error type'}) 