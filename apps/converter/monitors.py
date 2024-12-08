"""系统性能监控模块"""
import psutil
import os
from django.conf import settings
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
from .models import ConversionTask, ConversionHistory
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

class SystemMonitor:
    """系统资源监控器"""
    
    @staticmethod
    def get_system_metrics():
        """获取系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_usage = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used
            }
            
            # 磁盘使用情况
            disk = psutil.disk_usage(settings.MEDIA_ROOT)
            disk_usage = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            }
            
            # IO状态
            io_counters = psutil.disk_io_counters()
            io_stats = {
                'read_bytes': io_counters.read_bytes,
                'write_bytes': io_counters.write_bytes,
                'read_count': io_counters.read_count,
                'write_count': io_counters.write_count
            }
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'io_stats': io_stats
            }
            
        except Exception as e:
            logger.log_error('system_metrics_error', str(e))
            raise

class PerformanceMonitor:
    """性能监控器"""
    
    @staticmethod
    def get_conversion_metrics(time_range='day'):
        """获取转换性能指标"""
        try:
            now = timezone.now()
            
            if time_range == 'hour':
                start_time = now - timedelta(hours=1)
            elif time_range == 'day':
                start_time = now - timedelta(days=1)
            elif time_range == 'week':
                start_time = now - timedelta(weeks=1)
            else:
                raise ValueError('不支持的时间范围')
                
            # 获取时间段内的任务
            tasks = ConversionTask.objects.filter(
                created_at__gte=start_time
            )
            
            # 计算指标
            metrics = {
                'total_count': tasks.count(),
                'success_count': tasks.filter(status='completed').count(),
                'failed_count': tasks.filter(status='failed').count(),
                'avg_processing_time': tasks.filter(
                    status='completed'
                ).aggregate(
                    avg_time=Avg('processing_time')
                )['avg_time'],
                'format_distribution': tasks.values(
                    'original_format', 'target_format'
                ).annotate(
                    count=Count('id')
                ).order_by('-count')
            }
            
            return metrics
            
        except Exception as e:
            logger.log_error('conversion_metrics_error', str(e))
            raise

    @staticmethod
    def get_user_metrics():
        """获取用户使用指标"""
        try:
            today = timezone.now().date()
            
            metrics = {
                'daily_active_users': ConversionHistory.objects.filter(
                    created_at__date=today
                ).values('user').distinct().count(),
                
                'conversion_per_user': ConversionHistory.objects.values(
                    'user'
                ).annotate(
                    count=Count('id')
                ).aggregate(
                    avg=Avg('count')
                )['avg'],
                
                'peak_hours': ConversionHistory.objects.filter(
                    created_at__date=today
                ).extra(
                    {'hour': "EXTRACT(hour FROM created_at)"}
                ).values('hour').annotate(
                    count=Count('id')
                ).order_by('-count')[:5]
            }
            
            return metrics
            
        except Exception as e:
            logger.log_error('user_metrics_error', str(e))
            raise

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.performance_monitor = PerformanceMonitor()
        
    def check_system_health(self):
        """检查系统健康状态"""
        try:
            metrics = self.system_monitor.get_system_metrics()
            
            # 检查CPU使用率
            if metrics['cpu_usage'] > 90:
                logger.log_error('high_cpu_usage', 'CPU使用率过高', metrics)
                return False
                
            # 检查内存使用率
            if metrics['memory_usage']['percent'] > 90:
                logger.log_error('high_memory_usage', '内存使用率过高', metrics)
                return False
                
            # 检查磁盘空间
            if metrics['disk_usage']['percent'] > 90:
                logger.log_error('low_disk_space', '磁盘空间不足', metrics)
                return False
                
            return True
            
        except Exception as e:
            logger.log_error('health_check_error', str(e))
            raise
            
    def optimize_performance(self):
        """执行性能优化"""
        try:
            # 检查系统状态
            if not self.check_system_health():
                # 触发清理任务
                from .tasks import cleanup_old_files
                cleanup_old_files.delay()
                
            # 获取性能指标
            metrics = self.performance_monitor.get_conversion_metrics()
            
            # 根据指标调整配置
            if metrics['avg_processing_time'] > timedelta(minutes=5):
                # 可以在这里添加性能优化逻辑
                pass
                
            return True
            
        except Exception as e:
            logger.log_error('optimization_error', str(e))
            raise

    def get_optimization_suggestions(self):
        """获取优化建议"""
        try:
            suggestions = []
            metrics = self.system_monitor.get_system_metrics()
            
            # CPU使用率建议
            if metrics['cpu_usage'] > 80:
                suggestions.append({
                    'type': 'cpu',
                    'level': 'warning',
                    'message': '建议增加CPU资源或减少并发任务数'
                })
                
            # 内存使用建议
            if metrics['memory_usage']['percent'] > 80:
                suggestions.append({
                    'type': 'memory',
                    'level': 'warning',
                    'message': '建议增加内存或优化内存使用'
                })
                
            # 磁盘空间建议
            if metrics['disk_usage']['percent'] > 80:
                suggestions.append({
                    'type': 'disk',
                    'level': 'warning',
                    'message': '建议清理磁盘空间或扩展存储'
                })
                
            return suggestions
            
        except Exception as e:
            logger.log_error('suggestion_error', str(e))
            raise 