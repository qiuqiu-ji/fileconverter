"""安全监控系统"""
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging
import json
from datetime import timedelta

logger = logging.getLogger('security')

class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self):
        self.alert_threshold = getattr(settings, 'SECURITY_ALERT_THRESHOLD', {
            'attack': 10,  # 10次攻击
            'anomaly': 5,  # 5次异常
            'error': 100   # 100次错误
        })
        self.window = getattr(settings, 'SECURITY_MONITOR_WINDOW', 3600)  # 1小时
        
    def monitor_attacks(self):
        """监控攻击"""
        attacks = self._get_recent_events('attack')
        stats = {
            'sql_injection': 0,
            'xss': 0,
            'csrf': 0,
            'path_traversal': 0,
            'other': 0
        }
        
        for attack in attacks:
            attack_type = attack.get('type', 'other')
            stats[attack_type] = stats.get(attack_type, 0) + 1
            
        if sum(stats.values()) >= self.alert_threshold['attack']:
            self._generate_alert('attack', stats)
            
        return stats
        
    def detect_anomalies(self):
        """检测异常"""
        anomalies = []
        
        # 检查请求频率异常
        rate_anomalies = self._check_rate_anomalies()
        if rate_anomalies:
            anomalies.extend(rate_anomalies)
            
        # 检查行为异常
        behavior_anomalies = self._check_behavior_anomalies()
        if behavior_anomalies:
            anomalies.extend(behavior_anomalies)
            
        # 检查资源使用异常
        resource_anomalies = self._check_resource_anomalies()
        if resource_anomalies:
            anomalies.extend(resource_anomalies)
            
        if len(anomalies) >= self.alert_threshold['anomaly']:
            self._generate_alert('anomaly', anomalies)
            
        return anomalies
        
    def _check_rate_anomalies(self):
        """检查请求频率异常"""
        anomalies = []
        current_rate = self._get_current_request_rate()
        avg_rate = self._get_average_request_rate()
        
        if current_rate > avg_rate * 3:  # 当前频率超过平均值3倍
            anomalies.append({
                'type': 'high_request_rate',
                'current': current_rate,
                'average': avg_rate,
                'timestamp': timezone.now()
            })
            
        return anomalies
        
    def _check_behavior_anomalies(self):
        """检查行为异常"""
        anomalies = []
        
        # 检查登录失败
        login_failures = self._get_login_failures()
        if login_failures > 10:
            anomalies.append({
                'type': 'login_failures',
                'count': login_failures,
                'timestamp': timezone.now()
            })
            
        # 检查敏感操作
        sensitive_ops = self._get_sensitive_operations()
        if sensitive_ops > 5:
            anomalies.append({
                'type': 'sensitive_operations',
                'count': sensitive_ops,
                'timestamp': timezone.now()
            })
            
        return anomalies
        
    def _check_resource_anomalies(self):
        """检查资源使用异常"""
        anomalies = []
        
        # 检查CPU使用率
        cpu_usage = self._get_cpu_usage()
        if cpu_usage > 80:
            anomalies.append({
                'type': 'high_cpu_usage',
                'value': cpu_usage,
                'timestamp': timezone.now()
            })
            
        # 检查内存使用率
        memory_usage = self._get_memory_usage()
        if memory_usage > 80:
            anomalies.append({
                'type': 'high_memory_usage',
                'value': memory_usage,
                'timestamp': timezone.now()
            })
            
        return anomalies
        
    def _generate_alert(self, alert_type, data):
        """生成报警"""
        from .models import SecurityAlert
        
        alert = SecurityAlert.objects.create(
            type=alert_type,
            severity='high',
            data=json.dumps(data),
            timestamp=timezone.now()
        )
        
        # 发送通知
        self._send_alert_notification(alert)
        
    def _send_alert_notification(self, alert):
        """发送报警通知"""
        from django.core.mail import send_mail
        
        subject = f'Security Alert: {alert.type}'
        message = (
            f'Time: {alert.timestamp}\n'
            f'Type: {alert.type}\n'
            f'Severity: {alert.severity}\n'
            f'Data: {alert.data}\n'
        )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin[1] for admin in settings.ADMINS],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f'Failed to send alert notification: {e}')
            
    def _get_recent_events(self, event_type):
        """获取最近事件"""
        from .models import SecurityLog
        
        return SecurityLog.objects.filter(
            type=event_type,
            timestamp__gte=timezone.now() - timedelta(seconds=self.window)
        )
        
    def _get_current_request_rate(self):
        """获取当前请求频率"""
        key = 'request_count'
        count = cache.get(key, 0)
        return count / 60  # 每分钟请求数
        
    def _get_average_request_rate(self):
        """获取平均请求频率"""
        key = 'avg_request_rate'
        return cache.get(key, 0)
        
    def _get_login_failures(self):
        """获取登录失败次数"""
        from .models import SecurityLog
        
        return SecurityLog.objects.filter(
            type='login_failure',
            timestamp__gte=timezone.now() - timedelta(seconds=self.window)
        ).count()
        
    def _get_sensitive_operations(self):
        """获取敏感操作次数"""
        from .models import SecurityLog
        
        return SecurityLog.objects.filter(
            type='sensitive_operation',
            timestamp__gte=timezone.now() - timedelta(seconds=self.window)
        ).count()
        
    def _get_cpu_usage(self):
        """获取CPU使用率"""
        import psutil
        return psutil.cpu_percent()
        
    def _get_memory_usage(self):
        """获取内存使用率"""
        import psutil
        return psutil.virtual_memory().percent


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.thresholds = getattr(settings, 'PERFORMANCE_THRESHOLDS', {
            'response_time': 1.0,  # 1秒
            'cpu_usage': 80,      # 80%
            'memory_usage': 80,   # 80%
            'disk_usage': 90      # 90%
        })
        
    def monitor_response_times(self):
        """监控响应时间"""
        stats = {
            'avg_time': self._get_average_response_time(),
            'max_time': self._get_max_response_time(),
            'slow_requests': self._get_slow_requests(),
            'timestamp': timezone.now()
        }
        
        if stats['avg_time'] > self.thresholds['response_time']:
            self._generate_performance_alert('high_response_time', stats)
            
        return stats
        
    def monitor_resource_usage(self):
        """监控资源使用"""
        stats = {
            'cpu': self._get_cpu_usage(),
            'memory': self._get_memory_usage(),
            'disk': self._get_disk_usage(),
            'timestamp': timezone.now()
        }
        
        for resource, usage in stats.items():
            if usage > self.thresholds.get(f'{resource}_usage', 80):
                self._generate_performance_alert(f'high_{resource}_usage', {
                    'resource': resource,
                    'usage': usage
                })
                
        return stats
        
    def _get_average_response_time(self):
        """获取平均响应时间"""
        key = 'avg_response_time'
        return cache.get(key, 0)
        
    def _get_max_response_time(self):
        """获取最大响应时间"""
        key = 'max_response_time'
        return cache.get(key, 0)
        
    def _get_slow_requests(self):
        """获取慢请求数量"""
        from .models import RequestLog
        
        return RequestLog.objects.filter(
            response_time__gt=self.thresholds['response_time'],
            timestamp__gte=timezone.now() - timedelta(minutes=5)
        ).count()
        
    def _get_cpu_usage(self):
        """获取CPU使用率"""
        import psutil
        return psutil.cpu_percent()
        
    def _get_memory_usage(self):
        """获取内存使用率"""
        import psutil
        return psutil.virtual_memory().percent
        
    def _get_disk_usage(self):
        """获取磁盘使用率"""
        import psutil
        return psutil.disk_usage('/').percent
        
    def _generate_performance_alert(self, alert_type, data):
        """生成性能报警"""
        from .models import PerformanceAlert
        
        alert = PerformanceAlert.objects.create(
            type=alert_type,
            data=json.dumps(data),
            timestamp=timezone.now()
        )
        
        self._send_performance_alert(alert)
        
    def _send_performance_alert(self, alert):
        """发送性能报警"""
        from django.core.mail import send_mail
        
        subject = f'Performance Alert: {alert.type}'
        message = (
            f'Time: {alert.timestamp}\n'
            f'Type: {alert.type}\n'
            f'Data: {alert.data}\n'
        )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin[1] for admin in settings.ADMINS],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f'Failed to send performance alert: {e}')


class SecurityReporter:
    """安全报告生成器"""
    
    def generate_security_report(self, start_date=None, end_date=None):
        """生成安全报告"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=7)
        if not end_date:
            end_date = timezone.now()
            
        report = {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'summary': self._generate_summary(start_date, end_date),
            'attacks': self._analyze_attacks(start_date, end_date),
            'anomalies': self._analyze_anomalies(start_date, end_date),
            'alerts': self._analyze_alerts(start_date, end_date),
            'recommendations': self._generate_recommendations()
        }
        
        return report
        
    def generate_audit_report(self, start_date=None, end_date=None):
        """生成审计报告"""
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        report = {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'access_summary': self._analyze_access_logs(start_date, end_date),
            'user_activity': self._analyze_user_activity(start_date, end_date),
            'security_events': self._analyze_security_events(start_date, end_date),
            'compliance': self._check_compliance(),
            'recommendations': self._generate_audit_recommendations()
        }
        
        return report
        
    def _generate_summary(self, start_date, end_date):
        """生成摘要"""
        from .models import SecurityLog, SecurityAlert
        
        return {
            'total_events': SecurityLog.objects.filter(
                timestamp__range=(start_date, end_date)
            ).count(),
            'total_alerts': SecurityAlert.objects.filter(
                timestamp__range=(start_date, end_date)
            ).count(),
            'severity_distribution': self._get_severity_distribution(start_date, end_date),
            'top_issues': self._get_top_issues(start_date, end_date)
        }
        
    def _analyze_attacks(self, start_date, end_date):
        """分析攻击"""
        from .models import SecurityLog
        
        attacks = SecurityLog.objects.filter(
            type='attack',
            timestamp__range=(start_date, end_date)
        )
        
        return {
            'total': attacks.count(),
            'types': self._group_by_type(attacks, 'attack_type'),
            'sources': self._group_by_type(attacks, 'source_ip'),
            'targets': self._group_by_type(attacks, 'target_path'),
            'timeline': self._generate_timeline(attacks)
        }
        
    def _analyze_anomalies(self, start_date, end_date):
        """分析异常"""
        from .models import SecurityLog
        
        anomalies = SecurityLog.objects.filter(
            type='anomaly',
            timestamp__range=(start_date, end_date)
        )
        
        return {
            'total': anomalies.count(),
            'types': self._group_by_type(anomalies, 'anomaly_type'),
            'affected_users': self._group_by_type(anomalies, 'user'),
            'timeline': self._generate_timeline(anomalies)
        }
        
    def _analyze_alerts(self, start_date, end_date):
        """分析报警"""
        from .models import SecurityAlert
        
        alerts = SecurityAlert.objects.filter(
            timestamp__range=(start_date, end_date)
        )
        
        return {
            'total': alerts.count(),
            'by_severity': self._group_by_type(alerts, 'severity'),
            'by_type': self._group_by_type(alerts, 'type'),
            'response_times': self._analyze_response_times(alerts),
            'timeline': self._generate_timeline(alerts)
        }
        
    def _generate_recommendations(self):
        """生成建议"""
        recommendations = []
        
        # 基于攻击分析的建议
        attack_recommendations = self._get_attack_recommendations()
        if attack_recommendations:
            recommendations.extend(attack_recommendations)
            
        # 基于异常分析的建议
        anomaly_recommendations = self._get_anomaly_recommendations()
        if anomaly_recommendations:
            recommendations.extend(anomaly_recommendations)
            
        # 基于性能分析的建议
        performance_recommendations = self._get_performance_recommendations()
        if performance_recommendations:
            recommendations.extend(performance_recommendations)
            
        return recommendations
        
    def _group_by_type(self, queryset, field):
        """按类型分组"""
        return dict(queryset.values_list(field).annotate(count=models.Count('id')))
        
    def _generate_timeline(self, queryset):
        """生成时间线"""
        return list(
            queryset.values('timestamp')
            .annotate(count=models.Count('id'))
            .order_by('timestamp')
        )
        
    def _get_severity_distribution(self, start_date, end_date):
        """获取严重程度分布"""
        from .models import SecurityAlert
        
        return dict(
            SecurityAlert.objects.filter(
                timestamp__range=(start_date, end_date)
            ).values_list('severity')
            .annotate(count=models.Count('id'))
        )
        
    def _get_top_issues(self, start_date, end_date):
        """获取主要问题"""
        from .models import SecurityLog
        
        return list(
            SecurityLog.objects.filter(
                timestamp__range=(start_date, end_date)
            ).values('type', 'description')
            .annotate(count=models.Count('id'))
            .order_by('-count')[:10]
        )


class SecurityConfig:
    """安全配置管理器"""
    
    def __init__(self):
        self.required_settings = [
            'SECURITY_ENABLED',
            'SECURITY_ALERT_THRESHOLD',
            'SECURITY_MONITOR_WINDOW',
            'SECURITY_LOG_LEVEL',
        ]
        
    def validate_config(self):
        """验证配置"""
        missing_settings = []
        invalid_settings = []
        
        for setting in self.required_settings:
            if not hasattr(settings, setting):
                missing_settings.append(setting)
                continue
                
            value = getattr(settings, setting)
            if not self._is_valid_setting(setting, value):
                invalid_settings.append(setting)
                
        if missing_settings or invalid_settings:
            raise ValueError(
                f"Invalid security configuration:\n"
                f"Missing settings: {missing_settings}\n"
                f"Invalid settings: {invalid_settings}"
            )
            
        return True
        
    def apply_config(self):
        """应用配置"""
        if not self.validate_config():
            return False
            
        # 配置日志级别
        logging.getLogger('security').setLevel(
            getattr(settings, 'SECURITY_LOG_LEVEL')
        )
        
        # 配置缓存
        self._configure_cache()
        
        # 配置监控
        self._configure_monitoring()
        
        # 配置报警
        self._configure_alerts()
        
        return True
        
    def _is_valid_setting(self, setting, value):
        """验证设置值"""
        validators = {
            'SECURITY_ENABLED': lambda x: isinstance(x, bool),
            'SECURITY_ALERT_THRESHOLD': lambda x: isinstance(x, dict),
            'SECURITY_MONITOR_WINDOW': lambda x: isinstance(x, int) and x > 0,
            'SECURITY_LOG_LEVEL': lambda x: x in ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        }
        
        validator = validators.get(setting)
        if validator:
            return validator(value)
        return True
        
    def _configure_cache(self):
        """配置缓存"""
        cache.set('security_config_version', self._get_config_version())
        cache.set('security_enabled', getattr(settings, 'SECURITY_ENABLED'))
        
    def _configure_monitoring(self):
        """配置监控"""
        monitor = SecurityMonitor()
        monitor.window = getattr(settings, 'SECURITY_MONITOR_WINDOW')
        monitor.alert_threshold = getattr(settings, 'SECURITY_ALERT_THRESHOLD')
        
    def _configure_alerts(self):
        """配置报警"""
        from django.core.mail import get_connection
        
        # 测试邮件连接
        connection = get_connection()
        connection.open()
        connection.close()
        
    def _get_config_version(self):
        """获取配置版本"""
        import hashlib
        
        config_str = json.dumps({
            setting: getattr(settings, setting)
            for setting in self.required_settings
            if hasattr(settings, setting)
        }, sort_keys=True)
        
        return hashlib.md5(config_str.encode()).hexdigest() 