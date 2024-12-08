"""监控和统计测试"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask, ConversionStatistics
from apps.converter.monitoring import TaskMonitor, SystemMonitor
from datetime import timedelta
import psutil
import unittest
from unittest.mock import patch

User = get_user_model()

class MonitoringTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.task_monitor = TaskMonitor()
        self.system_monitor = SystemMonitor()

    def test_task_success_rate(self):
        """测试任务成功率统计"""
        # 创建测试数据
        statuses = {
            'completed': 7,
            'failed': 2,
            'pending': 1
        }
        
        for status, count in statuses.items():
            for _ in range(count):
                ConversionTask.objects.create(
                    user=self.user,
                    original_file='test.txt',
                    original_format='txt',
                    target_format='pdf',
                    status=status
                )

        # 计算成功率
        success_rate = self.task_monitor.calculate_success_rate()
        self.assertEqual(success_rate, 70.0)  # 7/10 * 100

    def test_average_processing_time(self):
        """测试平均处理时间统计"""
        # 创建已完成的任务
        processing_times = [30, 45, 60]  # 秒
        for seconds in processing_times:
            task = ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status='completed',
                processing_time=timedelta(seconds=seconds)
            )

        # 计算平均处理时间
        avg_time = self.task_monitor.calculate_average_processing_time()
        self.assertEqual(avg_time.total_seconds(), 45.0)

    @unittest.skipIf(not TaskMonitor()._check_psutil(), "psutil not available")
    def test_system_resource_usage(self):
        """测试系统资源使用统计"""
        # 获取系统资源使用情况
        stats = self.system_monitor.get_system_stats()
        
        # 验证统计数据
        self.assertIn('cpu_usage', stats)
        self.assertIn('memory_usage', stats)
        self.assertIn('disk_usage', stats)
        
        # 验证数值范围
        self.assertGreaterEqual(stats['cpu_usage'], 0)
        self.assertLessEqual(stats['cpu_usage'], 100)
        self.assertGreaterEqual(stats['memory_usage'], 0)
        self.assertLessEqual(stats['memory_usage'], 100)

    def test_user_quotas(self):
        """测试用户配额统计"""
        # 创建测试任务
        file_sizes = [1024 * 1024 * i for i in range(1, 4)]  # 1MB, 2MB, 3MB
        for size in file_sizes:
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status='completed',
                file_size=size
            )

        # 计算存储使用量
        storage_usage = self.task_monitor.calculate_user_storage(self.user)
        self.assertEqual(storage_usage, sum(file_sizes))

        # 验证配额限制
        self.user.storage_quota = 1024 * 1024 * 5  # 5MB
        self.user.save()
        quota_status = self.task_monitor.check_user_quota(self.user)
        self.assertEqual(quota_status['used_percentage'], 120.0)  # 6MB/5MB * 100
        self.assertTrue(quota_status['exceeded'])

    def test_error_statistics(self):
        """测试错误统计"""
        # 创建不同错误的任务
        error_types = {
            'format_error': 3,
            'system_error': 2,
            'network_error': 1
        }
        
        for error_type, count in error_types.items():
            for _ in range(count):
                ConversionTask.objects.create(
                    user=self.user,
                    original_file='test.txt',
                    original_format='txt',
                    target_format='pdf',
                    status='failed',
                    error_message=error_type
                )

        # 统计错误
        error_stats = self.task_monitor.analyze_errors()
        self.assertEqual(error_stats['format_error'], 3)
        self.assertEqual(error_stats['system_error'], 2)
        self.assertEqual(error_stats['network_error'], 1)

    def test_performance_metrics(self):
        """测试性能指标"""
        # 记录性能数据
        for _ in range(5):
            ConversionStatistics.objects.create(
                cpu_usage=50.0,
                memory_usage=60.0,
                task_count=10,
                error_count=1,
                average_processing_time=timedelta(seconds=30)
            )

        # 计算性能指标
        metrics = self.system_monitor.calculate_performance_metrics()
        self.assertIn('avg_cpu_usage', metrics)
        self.assertIn('avg_memory_usage', metrics)
        self.assertIn('task_success_rate', metrics)
        self.assertIn('avg_processing_time', metrics)

    def test_monitoring_alerts(self):
        """测试监控告警"""
        # 模拟高负载
        stats = {
            'cpu_usage': 95.0,
            'memory_usage': 90.0,
            'disk_usage': 85.0
        }
        
        alerts = self.system_monitor.check_alerts(stats)
        self.assertTrue(alerts['high_cpu'])
        self.assertTrue(alerts['high_memory'])
        self.assertTrue(alerts['high_disk'])

        # 模拟正常负载
        stats = {
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0
        }
        
        alerts = self.system_monitor.check_alerts(stats)
        self.assertFalse(alerts['high_cpu'])
        self.assertFalse(alerts['high_memory'])
        self.assertFalse(alerts['high_disk']) 

    def test_system_stats_without_psutil(self):
        """测试在没有psutil的情况下的系统统计"""
        with patch('apps.converter.monitoring.SystemMonitor._check_psutil', return_value=False):
            monitor = SystemMonitor()
            stats = monitor.get_system_stats()
            self.assertEqual(stats['cpu_usage'], 0)
            self.assertEqual(stats['memory_usage'], 0)
            self.assertEqual(stats['disk_usage'], 0)

    def tearDown(self):
        """清理测试数据"""
        ConversionTask.objects.all().delete()
        ConversionStatistics.objects.all().delete() 