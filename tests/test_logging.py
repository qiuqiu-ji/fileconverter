"""日志分析测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask, ConversionHistory
from apps.security.models import SecurityLog
from apps.converter.log_analyzer import LogAnalyzer
import logging
import json

User = get_user_model()

class LogAnalysisTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.analyzer = LogAnalyzer()
        self.logger = logging.getLogger('apps.converter')

    def test_error_pattern_analysis(self):
        """测试错误模式分析"""
        # 创建错误日志
        error_patterns = [
            "Memory allocation failed",
            "Memory allocation failed",
            "Disk space full",
            "Network timeout",
            "Network timeout",
            "Network timeout"
        ]
        
        for error in error_patterns:
            self.logger.error(error)
            SecurityLog.objects.create(
                level='ERROR',
                message=error,
                user=self.user
            )

        # 分析错误模式
        patterns = self.analyzer.analyze_error_patterns()
        self.assertEqual(patterns['Network timeout'], 3)
        self.assertEqual(patterns['Memory allocation failed'], 2)
        self.assertEqual(patterns['Disk space full'], 1)

    def test_user_behavior_analysis(self):
        """测试用户行为分析"""
        # 创建用户活动记录
        for _ in range(5):
            ConversionHistory.objects.create(
                user=self.user,
                task=ConversionTask.objects.create(
                    user=self.user,
                    original_file='test.txt',
                    original_format='txt',
                    target_format='pdf'
                ),
                ip_address='127.0.0.1',
                user_agent='Mozilla/5.0'
            )

        # 分析用户行为
        behavior = self.analyzer.analyze_user_behavior(self.user)
        self.assertEqual(behavior['conversion_count'], 5)
        self.assertEqual(behavior['most_used_format'], 'pdf')
        self.assertIn('127.0.0.1', behavior['ip_addresses'])

    def test_security_log_analysis(self):
        """测试安全日志分析"""
        # 创建安全日志
        security_events = [
            {'type': 'login_failed', 'ip': '192.168.1.1'},
            {'type': 'login_failed', 'ip': '192.168.1.1'},
            {'type': 'suspicious_file', 'ip': '192.168.1.2'},
            {'type': 'rate_limit_exceeded', 'ip': '192.168.1.3'}
        ]
        
        for event in security_events:
            SecurityLog.objects.create(
                level='WARNING',
                message=json.dumps(event),
                user=self.user
            )

        # 分析安全事件
        security_analysis = self.analyzer.analyze_security_logs()
        self.assertEqual(security_analysis['login_failed'], 2)
        self.assertEqual(security_analysis['suspicious_ips'], ['192.168.1.1'])

    def test_performance_log_analysis(self):
        """测试性能日志分析"""
        # 创建性能日志
        performance_logs = [
            {'cpu': 80, 'memory': 70, 'response_time': 1.5},
            {'cpu': 90, 'memory': 85, 'response_time': 2.0},
            {'cpu': 70, 'memory': 60, 'response_time': 1.0}
        ]
        
        for log in performance_logs:
            self.logger.info(f"Performance metrics: {json.dumps(log)}")

        # 分析性能日志
        performance = self.analyzer.analyze_performance_logs()
        self.assertEqual(performance['avg_cpu'], 80)
        self.assertEqual(performance['avg_memory'], 71.67)
        self.assertEqual(performance['avg_response_time'], 1.5)

    def test_log_aggregation(self):
        """测试日志聚合"""
        # 创建不同类型的日志
        log_types = ['ERROR', 'WARNING', 'INFO']
        for level in log_types:
            for _ in range(3):
                SecurityLog.objects.create(
                    level=level,
                    message=f'Test {level} message',
                    user=self.user
                )

        # 聚合日志
        aggregated = self.analyzer.aggregate_logs()
        self.assertEqual(aggregated['ERROR'], 3)
        self.assertEqual(aggregated['WARNING'], 3)
        self.assertEqual(aggregated['INFO'], 3)

    def test_trend_analysis(self):
        """测试趋势分析"""
        # 创建历史数据
        for i in range(7):
            for _ in range(i + 1):  # 递增的任务数
                ConversionTask.objects.create(
                    user=self.user,
                    original_file='test.txt',
                    original_format='txt',
                    target_format='pdf',
                    status='completed'
                )

        # 分析趋势
        trends = self.analyzer.analyze_trends()
        self.assertTrue(trends['is_increasing'])
        self.assertEqual(trends['growth_rate'], 100.0)  # (7-1)/6 * 100 