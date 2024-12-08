"""错误处理测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ..error_handlers import (
    ErrorRecoveryManager,
    TaskMonitor,
    ConversionError,
    FileValidationError,
    handle_conversion_errors
)
from ..models import ConversionTask, ErrorLog
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

User = get_user_model()

class ErrorHandlingTests(TestCase):
    """错误处理测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.recovery_manager = ErrorRecoveryManager()
        
    def test_task_recovery(self):
        """测试任务恢复"""
        # 创建失败的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_format='jpg',
            target_format='png',
            status='failed',
            error_message='Test error'
        )
        
        # 尝试恢复任务
        success = self.recovery_manager.recover_failed_task(task.id)
        self.assertTrue(success)
        
        # 验证任务状态
        task.refresh_from_db()
        self.assertEqual(task.status, 'pending')
        self.assertIsNone(task.error_message)
        self.assertEqual(task.retry_count, 1)
        
    def test_max_retries(self):
        """测试最大重试次数"""
        # 创建已达到最大重试次数的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_format='jpg',
            target_format='png',
            status='failed',
            retry_count=3
        )
        
        # 清理失败任务
        cleaned = self.recovery_manager.cleanup_failed_tasks()
        self.assertEqual(cleaned, 1)
        
        # 验证任务已被删除
        with self.assertRaises(ConversionTask.DoesNotExist):
            ConversionTask.objects.get(id=task.id)
            
        # 验证错误日志
        error_log = ErrorLog.objects.get(task_id=task.id)
        self.assertEqual(error_log.error_type, 'max_retries_exceeded')

class TaskMonitorTests(TestCase):
    """任务监控测试"""
    
    def setUp(self):
        self.monitor = TaskMonitor()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_stuck_task_detection(self):
        """测试卡住任务检测"""
        # 创建一个长时间处理的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_format='jpg',
            target_format='png',
            status='processing',
            created_at=timezone.now() - timedelta(hours=1)
        )
        
        # 检查任务健康状态
        is_healthy = self.monitor.check_task_health(task.id)
        self.assertFalse(is_healthy)
        
    def test_task_metrics(self):
        """测试任务指标"""
        # 创建一些测试任务
        statuses = ['completed', 'failed', 'processing']
        for status in statuses:
            ConversionTask.objects.create(
                user=self.user,
                original_format='jpg',
                target_format='png',
                status=status
            )
            
        metrics = self.monitor.get_task_metrics()
        
        self.assertEqual(metrics['total_tasks'], 3)
        self.assertEqual(metrics['failed_tasks'], 1)
        self.assertEqual(metrics['processing_tasks'], 1)

@patch('apps.converter.tasks.convert_file_task.delay')
class ErrorDecoratorTests(TestCase):
    """错误处理装饰器测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_validation_error_handling(self, mock_task):
        """测试验证错误处理"""
        @handle_conversion_errors
        def test_view(request):
            raise FileValidationError('Invalid file')
            
        response = test_view(None)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error_code'], 'VALIDATION_ERROR')
        
    def test_conversion_error_handling(self, mock_task):
        """测试转换错误处理"""
        @handle_conversion_errors
        def test_view(request):
            raise ConversionError('Conversion failed')
            
        response = test_view(None)
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['error_code'], 'CONVERSION_ERROR')
        
    def test_unexpected_error_handling(self, mock_task):
        """测试未预期错误处理"""
        @handle_conversion_errors
        def test_view(request):
            raise Exception('Unexpected error')
            
        response = test_view(None)
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['error_code'], 'INTERNAL_ERROR') 