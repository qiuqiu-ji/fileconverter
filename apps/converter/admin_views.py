from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import ConversionTask, ConversionHistory
import os
import psutil

@staff_member_required
def system_monitor(request):
    """系统监控面板"""
    # 获取系统状态
    cpu_usage = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 获取转换统计
    today = timezone.now()
    last_week = today - timedelta(days=7)
    
    stats = {
        'total_conversions': ConversionTask.objects.count(),
        'today_conversions': ConversionTask.objects.filter(
            created_at__date=today.date()
        ).count(),
        'failed_conversions': ConversionTask.objects.filter(
            status='failed'
        ).count(),
        'active_users': ConversionHistory.objects.filter(
            created_at__gte=last_week
        ).values('user').distinct().count(),
    }
    
    # 获取格式统计
    format_stats = ConversionTask.objects.values(
        'original_format', 'target_format'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # 获取错误日志
    error_tasks = ConversionTask.objects.filter(
        status='failed'
    ).order_by('-created_at')[:10]
    
    context = {
        'system_stats': {
            'cpu_usage': cpu_usage,
            'memory_used': memory.percent,
            'disk_used': disk.percent,
        },
        'conversion_stats': stats,
        'format_stats': format_stats,
        'error_tasks': error_tasks,
    }
    
    return render(request, 'admin/system_monitor.html', context) 