"""监控和统计功能"""
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from datetime import timedelta
import psutil

class TaskMonitor:
    def calculate_success_rate(self):
        """计算任务成功率"""
        from .models import ConversionTask
        total = ConversionTask.objects.exclude(status='pending').count()
        if total == 0:
            return 0.0
        completed = ConversionTask.objects.filter(status='completed').count()
        return (completed / total) * 100

    def calculate_average_processing_time(self):
        """计算平均处理时间"""
        from .models import ConversionTask
        result = ConversionTask.objects.filter(
            status='completed',
            processing_time__isnull=False
        ).aggregate(avg_time=Avg('processing_time'))
        return result['avg_time'] or timedelta()

    def calculate_user_storage(self, user):
        """计算用户存储使用量"""
        from .models import ConversionTask
        result = ConversionTask.objects.filter(
            user=user
        ).aggregate(total_size=Sum('file_size'))
        return result['total_size'] or 0

    def check_user_quota(self, user):
        """检查用户配额状态"""
        used_storage = self.calculate_user_storage(user)
        quota = user.storage_quota
        used_percentage = (used_storage / quota) * 100 if quota > 0 else 0
        return {
            'used': used_storage,
            'quota': quota,
            'used_percentage': used_percentage,
            'exceeded': used_storage > quota
        }

    def analyze_errors(self):
        """分析错误统计"""
        from .models import ConversionTask
        return dict(
            ConversionTask.objects.filter(
                status='failed'
            ).values('error_message').annotate(
                count=Count('id')
            ).values_list('error_message', 'count')
        )

class SystemMonitor:
    def __init__(self):
        self.psutil_available = self._check_psutil()

    def _check_psutil(self):
        """检查psutil是否可用"""
        try:
            import psutil
            return True
        except ImportError:
            return False

    def get_system_stats(self):
        """获取系统资源使用情况"""
        if not self.psutil_available:
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0
            }

        stats = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
        return stats

    def calculate_performance_metrics(self):
        """计算性能指标"""
        from .models import ConversionStatistics
        metrics = ConversionStatistics.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).aggregate(
            avg_cpu_usage=Avg('cpu_usage'),
            avg_memory_usage=Avg('memory_usage'),
            task_success_rate=Avg('task_success_rate'),
            avg_processing_time=Avg('average_processing_time')
        )
        return metrics

    def check_alerts(self, stats):
        """检查是否需要触发告警"""
        thresholds = {
            'cpu': 90,
            'memory': 85,
            'disk': 80
        }
        
        return {
            'high_cpu': stats['cpu_usage'] > thresholds['cpu'],
            'high_memory': stats['memory_usage'] > thresholds['memory'],
            'high_disk': stats['disk_usage'] > thresholds['disk']
        } 