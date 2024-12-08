"""错误处理测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.core.exceptions import *
from apps.converter.models import ConversionTask
import json

User = get_user_model()

class ErrorHandlingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_file_validation_error(self):
        """测试文件验证错误"""
        # 测试无效文件类型
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b"Invalid file",
            content_type="application/x-msdownload"
        )
        
        response = self.client.post(reverse('converter:upload'), {
            'file': invalid_file
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Unsupported file type', data['error'])

    def test_quota_exceeded_error(self):
        """测试配额超限错误"""
        # 设置用户配额为1MB
        self.user.storage_quota = 1024 * 1024
        self.user.save()
        
        # 上传2MB文件
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (2 * 1024 * 1024),
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('converter:upload'), {
            'file': large_file
        })
        
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.content)
        self.assertIn('quota exceeded', data['error'].lower())

    def test_rate_limit_error(self):
        """测试速率限制错误"""
        # 连续发送请求直到触发限制
        for _ in range(101):  # 假设限制是100次/小时
            response = self.client.post(reverse('converter:upload'), {
                'file': SimpleUploadedFile("test.txt", b"test")
            })
            if response.status_code == 429:
                data = json.loads(response.content)
                self.assertIn('rate limit', data['error'].lower())
                break
        else:
            self.fail("Rate limit not enforced")

    def test_security_error(self):
        """测试安全错误"""
        # 上传包含恶意代码的文件
        malicious_file = SimpleUploadedFile(
            "test.txt",
            b"<script>alert('xss')</script>",
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('converter:upload'), {
            'file': malicious_file
        })
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('security', data['error'].lower())

    def test_conversion_error(self):
        """测试转换错误"""
        # 创建一个无效的转换任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='invalid'
        )
        
        response = self.client.post(reverse('converter:convert'), {
            'task_id': task.id
        })
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data['status'])

    def test_unexpected_error(self):
        """测试意外错误"""
        # 模拟意外错误
        with self.assertLogs('apps.core', level='ERROR') as logs:
            response = self.client.post(reverse('converter:convert'), {
                'task_id': 'invalid-id'
            })
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('unexpected error', data['error'].lower())
            self.assertTrue(any('Unexpected error' in log for log in logs.output)) 

    def test_error_notification(self):
        """测试错误通知"""
        from apps.core.handlers import ErrorHandler
        from django.core import mail
        
        # 创建一个测试错误
        try:
            raise ValueError("Test error for notification")
        except ValueError as e:
            error_info = ErrorHandler.handle_error(self.client.request, e)
        
        # 验证邮件通知
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Test error for notification', mail.outbox[0].subject)
        self.assertIn(error_info['error_id'], mail.outbox[0].body)

    def test_error_statistics(self):
        """测试错误统计"""
        from apps.core.monitoring import ErrorMonitor
        
        # 生成一些测试错误
        test_errors = [
            {'error_id': 'test1', 'exception': 'ValueError', 'url': '/test1'},
            {'error_id': 'test2', 'exception': 'ValueError', 'url': '/test2'},
            {'error_id': 'test3', 'exception': 'TypeError', 'url': '/test3'},
        ]
        
        for error in test_errors:
            ErrorMonitor.record_error(error)
        
        # 获取统计数据
        stats = ErrorMonitor.get_error_stats(days=1)
        
        # 验证统计结果
        self.assertEqual(stats['total_errors'], 3)
        self.assertEqual(len(stats['common_errors']), 2)  # ValueError和TypeError

    def test_maintenance_mode(self):
        """测试维护模式"""
        from django.conf import settings
        from django.test.utils import override_settings
        
        # 启用维护模式
        with override_settings(MAINTENANCE_MODE=True):
            # 普通用户访问
            response = self.client.get('/')
            self.assertEqual(response.status_code, 503)
            self.assertTemplateUsed(response, 'errors/maintenance.html')
            
            # 管理员访问
            self.client.login(username='admin', password='admin123')
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            
            # API访问
            response = self.client.get('/api/v1/status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()['status'], 'maintenance') 