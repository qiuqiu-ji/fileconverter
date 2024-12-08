"""性能测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from ..monitors import SystemMonitor, PerformanceMonitor
from ..models import ConversionTask, ConversionHistory
import time

User = get_user_model()

class SystemMonitorTests(TestCase):
    """系统监控测试"""
    
    def setUp(self):
        self.monitor = SystemMonitor()
        
    def test_system_metrics(self):
        """测试系统指标获取"""
        metrics = self.monitor.get_system_metrics()
        
        # 验证返回的指标
        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)
        self.assertIn('io_stats', metrics)
        
        # 验证值的合理性
        self.assertGreaterEqual(metrics['cpu_usage'], 0)
        self.assertLessEqual(metrics['cpu_usage'], 100)
        self.assertGreater(metrics['memory_usage']['total'], 0)
        self.assertGreater(metrics['disk_usage']['total'], 0)

class PerformanceMonitorTests(TestCase):
    """性能监控测试"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_conversion_metrics(self):
        """测试转换指标"""
        # 创建一些测试数据
        for i in range(5):
            task = ConversionTask.objects.create(
                user=self.user,
                original_format='jpg',
                target_format='png',
                status='completed' if i < 3 else 'failed'
            )
            ConversionHistory.objects.create(
                user=self.user,
                task=task
            )
            
        metrics = self.monitor.get_conversion_metrics()
        
        self.assertEqual(metrics['total_count'], 5)
        self.assertEqual(metrics['success_count'], 3)
        self.assertEqual(metrics['failed_count'], 2)
        
    def test_user_metrics(self):
        """测试用户指标"""
        # 创建测试数据
        for _ in range(3):
            task = ConversionTask.objects.create(
                user=self.user,
                original_format='jpg',
                target_format='png',
                status='completed'
            )
            ConversionHistory.objects.create(
                user=self.user,
                task=task
            )
            
        metrics = self.monitor.get_user_metrics()
        
        self.assertEqual(metrics['daily_active_users'], 1)
        self.assertEqual(metrics['conversion_per_user'], 3.0)
        self.assertTrue('peak_hours' in metrics)

class PerformanceTests(TestCase):
    """性能测试"""
    
    def test_conversion_speed(self):
        """测试转换速度"""
        from ..converters import ImageConverter
        
        converter = ImageConverter()
        test_file = 'tests/test_files/test.jpg'
        output_file = 'tests/test_files/output.png'
        
        start_time = time.time()
        converter.convert(test_file, output_file)
        end_time = time.time()
        
        # 验证转换时间在合理范围内
        conversion_time = end_time - start_time
        self.assertLess(conversion_time, 5.0)  # 假设5秒是合理的最大转换时间
        
        # 清理测试文件
        if os.path.exists(output_file):
            os.remove(output_file) 