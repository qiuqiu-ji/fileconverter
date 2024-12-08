"""安全相关视图"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models import Count
from .models import SecurityLog, SecurityAlert

@user_passes_test(lambda u: u.is_staff)
def security_logs(request):
    """安全日志列表"""
    logs = SecurityLog.objects.select_related('user').all()
    
    # 过滤条件
    level = request.GET.get('level')
    if level:
        logs = logs.filter(level=level)
        
    # 统计信息
    stats = {
        'total': logs.count(),
        'by_level': dict(logs.values('level').annotate(count=Count('id')).values_list('level', 'count')),
        'recent_ips': logs.values('ip_address').distinct()[:10]
    }
    
    return render(request, 'security/logs.html', {
        'logs': logs,
        'stats': stats
    })

@user_passes_test(lambda u: u.is_staff)
def security_alerts(request):
    """安全告警列表"""
    alerts = SecurityAlert.objects.select_related('resolved_by').all()
    
    # 过滤条件
    severity = request.GET.get('severity')
    if severity:
        alerts = alerts.filter(severity=severity)
        
    is_resolved = request.GET.get('is_resolved')
    if is_resolved is not None:
        alerts = alerts.filter(is_resolved=is_resolved == 'true')
    
    return render(request, 'security/alerts.html', {
        'alerts': alerts
    })

@user_passes_test(lambda u: u.is_staff)
def resolve_alert(request, alert_id):
    """解决告警"""
    alert = get_object_or_404(SecurityAlert, id=alert_id)
    
    if not alert.is_resolved:
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        
        messages.success(request, _('Alert marked as resolved'))
    
    return redirect('security:alerts')

@user_passes_test(lambda u: u.is_staff)
def security_stats(request):
    """安全统计信息"""
    from apps.converter.log_analyzer import LogAnalyzer
    analyzer = LogAnalyzer()
    
    # 获取统计数据
    stats = {
        'error_patterns': analyzer.analyze_error_patterns(),
        'security_events': analyzer.analyze_security_logs(),
        'log_summary': analyzer.aggregate_logs(),
        'trends': analyzer.analyze_trends()
    }
    
    return render(request, 'security/stats.html', {
        'stats': stats
    }) 