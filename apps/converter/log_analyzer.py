"""日志分析器"""
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
import re

class LogAnalyzer:
    def analyze_error_patterns(self):
        """分析错误模式"""
        from apps.security.models import SecurityLog
        
        # 获取错误日志
        error_logs = SecurityLog.objects.filter(
            level='ERROR'
        ).values('message').annotate(
            count=Count('id')
        )
        
        # 统计错误模式
        patterns = {}
        for log in error_logs:
            patterns[log['message']] = log['count']
        return patterns

    def analyze_user_behavior(self, user):
        """分析用户行为"""
        from apps.converter.models import ConversionHistory, ConversionTask
        
        # 获取用户转换历史
        history = ConversionHistory.objects.filter(user=user)
        tasks = ConversionTask.objects.filter(user=user)
        
        # 统计转换格式
        formats = tasks.values('target_format').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 统计IP地址
        ip_addresses = set(history.values_list('ip_address', flat=True))
        
        return {
            'conversion_count': tasks.count(),
            'most_used_format': formats[0]['target_format'] if formats else None,
            'ip_addresses': list(ip_addresses)
        }

    def analyze_security_logs(self):
        """分析安全日志"""
        from apps.security.models import SecurityLog
        
        # 获取安全日志
        security_logs = SecurityLog.objects.filter(
            level='WARNING'
        )
        
        # 分析事件类型
        event_types = {}
        suspicious_ips = set()
        
        for log in security_logs:
            try:
                event = json.loads(log.message)
                event_type = event.get('type')
                if event_type:
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                
                # 检查可疑IP
                if event_type == 'login_failed':
                    suspicious_ips.add(event.get('ip'))
            except json.JSONDecodeError:
                continue
        
        return {
            **event_types,
            'suspicious_ips': list(suspicious_ips)
        }

    def analyze_performance_logs(self):
        """分析���能日志"""
        from apps.converter.models import ConversionStatistics
        
        # 获取最近的性能数据
        recent_stats = ConversionStatistics.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        )
        
        if not recent_stats.exists():
            return {
                'avg_cpu': 0,
                'avg_memory': 0,
                'avg_response_time': 0
            }
        
        # 计算平均值
        stats = recent_stats.aggregate(
            avg_cpu=Avg('cpu_usage'),
            avg_memory=Avg('memory_usage'),
            avg_response_time=Avg('response_time')
        )
        
        # 保留两位小数
        return {
            'avg_cpu': round(stats['avg_cpu'] or 0, 2),
            'avg_memory': round(stats['avg_memory'] or 0, 2),
            'avg_response_time': round(stats['avg_response_time'] or 0, 2)
        }

    def aggregate_logs(self):
        """聚合日志"""
        from apps.security.models import SecurityLog
        
        # 按级别统计日志数量
        return dict(
            SecurityLog.objects.values('level').annotate(
                count=Count('id')
            ).values_list('level', 'count')
        )

    def analyze_trends(self):
        """分析趋势"""
        from apps.converter.models import ConversionTask
        
        # 获取每日任务数量
        daily_counts = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = ConversionTask.objects.filter(
                created_at__date=date,
                status='completed'
            ).count()
            daily_counts.append(count)
        
        # 计算增长率
        if len(daily_counts) > 1 and daily_counts[-1] > 0:
            growth_rate = ((daily_counts[0] - daily_counts[-1]) / daily_counts[-1]) * 100
        else:
            growth_rate = 0
        
        return {
            'daily_counts': daily_counts,
            'is_increasing': daily_counts[0] > daily_counts[-1],
            'growth_rate': round(growth_rate, 2)
        } 