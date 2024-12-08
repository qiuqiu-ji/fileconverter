"""安全监控测试"""
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from django.test.utils import override_settings
from apps.security.monitoring import (
    SecurityMonitor,
    PerformanceMonitor,
    SecurityReporter,
    SecurityConfig
)
from apps.security.models import SecurityLog, SecurityAlert, PerformanceAlert
from datetime import timedelta
import json

class SecurityMonitorTest(TestCase):
    def setUp(self):
        self.monitor = SecurityMonitor()
        
    def test_attack_monitoring(self):
        """测试攻击监控"""
        # 创建攻击记录
        for _ in range(5):
            SecurityLog.objects.create(
                type='attack',
                attack_type='sql_injection',
                source_ip='192.168.1.1',
                timestamp=timezone.now()
            )
            
        stats = self.monitor.monitor_attacks()
        
        self.assertEqual(stats['sql_injection'], 5)
        self.assertEqual(stats['xss'], 0)
        
    def test_anomaly_detection(self):
        """测试异常检测"""
        # 模拟高频率请求
        cache.set('request_count', 1000)  # 每分钟1000请求
        
        anomalies = self.monitor.detect_anomalies()
        
        self.assertTrue(any(
            a['type'] == 'high_request_rate'
            for a in anomalies
        ))
        
    def test_resource_monitoring(self):
        """测试资源监控"""
        # 模拟高资源使用
        with override_settings(MOCK_CPU_USAGE=85):
            anomalies = self.monitor._check_resource_anomalies()
            
        self.assertTrue(any(
            a['type'] == 'high_cpu_usage'
            for a in anomalies
        ))
        
    def test_alert_generation(self):
        """测试报警生成"""
        data = {
            'type': 'sql_injection',
            'count': 10,
            'source_ip': '192.168.1.1'
        }
        
        self.monitor._generate_alert('attack', data)
        
        alert = SecurityAlert.objects.latest('timestamp')
        self.assertEqual(alert.type, 'attack')
        self.assertEqual(json.loads(alert.data)['count'], 10)


class PerformanceMonitorTest(TestCase):
    def setUp(self):
        self.monitor = PerformanceMonitor()
        
    def test_response_time_monitoring(self):
        """测试响应时间监控"""
        # 设置慢响应
        cache.set('avg_response_time', 2.0)  # 2秒
        
        stats = self.monitor.monitor_response_times()
        
        self.assertTrue(stats['avg_time'] > 1.0)
        self.assertTrue(
            PerformanceAlert.objects.filter(
                type='high_response_time'
            ).exists()
        )
        
    def test_resource_usage_monitoring(self):
        """测试资源使用监控"""
        with override_settings(MOCK_MEMORY_USAGE=85):
            stats = self.monitor.monitor_resource_usage()
            
        self.assertTrue(stats['memory'] > 80)
        self.assertTrue(
            PerformanceAlert.objects.filter(
                type='high_memory_usage'
            ).exists()
        )


class SecurityReporterTest(TestCase):
    def setUp(self):
        self.reporter = SecurityReporter()
        
    def test_security_report_generation(self):
        """测试安全报告生成"""
        # 创建测试数据
        SecurityLog.objects.create(
            type='attack',
            attack_type='sql_injection',
            source_ip='192.168.1.1',
            timestamp=timezone.now()
        )
        
        report = self.reporter.generate_security_report()
        
        self.assertEqual(report['summary']['total_events'], 1)
        self.assertEqual(
            report['attacks']['types'].get('sql_injection'),
            1
        )
        
    def test_audit_report_generation(self):
        """测试审计报告生成"""
        # 创建测试数据
        SecurityLog.objects.create(
            type='access',
            user='testuser',
            action='login',
            timestamp=timezone.now()
        )
        
        report = self.reporter.generate_audit_report()
        
        self.assertTrue('access_summary' in report)
        self.assertTrue('user_activity' in report)


class SecurityConfigTest(TestCase):
    def setUp(self):
        self.config = SecurityConfig()
        
    @override_settings(
        SECURITY_ENABLED=True,
        SECURITY_ALERT_THRESHOLD={'attack': 10},
        SECURITY_MONITOR_WINDOW=3600,
        SECURITY_LOG_LEVEL='INFO'
    )
    def test_config_validation(self):
        """测试配置验证"""
        self.assertTrue(self.config.validate_config())
        
    @override_settings(SECURITY_ENABLED=None)
    def test_invalid_config(self):
        """测试无效配置"""
        with self.assertRaises(ValueError):
            self.config.validate_config()
            
    def test_config_application(self):
        """测试配置应用"""
        with override_settings(
            SECURITY_ENABLED=True,
            SECURITY_ALERT_THRESHOLD={'attack': 10},
            SECURITY_MONITOR_WINDOW=3600,
            SECURITY_LOG_LEVEL='INFO'
        ):
            self.assertTrue(self.config.apply_config())
            
        self.assertTrue(cache.get('security_enabled'))
        self.assertIsNotNone(cache.get('security_config_version')) 