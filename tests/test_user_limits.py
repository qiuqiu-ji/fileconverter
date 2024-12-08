"""用户配额和限制测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.converter.models import ConversionTask
from datetime import timedelta

class UserLimitsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            daily_conversion_limit=5,
            storage_quota=1024 * 1024  # 1MB
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_daily_conversion_limit(self):
        """测试每日转换限制"""
        # 创建测试文件
        test_file = SimpleUploadedFile(
            "test.txt",
            b"Hello World!",
            content_type="text/plain"
        )

        # 尝试超过限制次数的转换
        for i in range(6):  # 超过限制(5)
            response = self.client.post(reverse('converter:upload_session'), {
                'filename': f'test{i}.txt',
                'filesize': len(test_file.read()),
                'target_format': 'pdf'
            })
            test_file.seek(0)
            
            if i < 5:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 429)  # Too Many Requests

    def test_storage_quota(self):
        """测试存储配额限制"""
        # 创建一个超过配额的大文件
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (2 * 1024 * 1024),  # 2MB
            content_type="text/plain"
        )

        response = self.client.post(reverse('converter:upload_session'), {
            'filename': 'large.txt',
            'filesize': large_file.size,
            'target_format': 'pdf'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Storage quota exceeded', str(response.content))

    def test_quota_reset(self):
        """测试配额重置"""
        # 创建昨天的转换记录
        yesterday = timezone.now() - timedelta(days=1)
        for i in range(5):
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                created_at=yesterday
            )

        # 验证今天可以继续转换
        test_file = SimpleUploadedFile(
            "test.txt",
            b"Hello World!",
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('converter:upload_session'), {
            'filename': 'test.txt',
            'filesize': len(test_file.read()),
            'target_format': 'pdf'
        })
        
        self.assertEqual(response.status_code, 200)

    def test_concurrent_uploads(self):
        """测试并发上传限制"""
        files = [
            SimpleUploadedFile(
                f"test{i}.txt",
                b"Hello World!",
                content_type="text/plain"
            ) for i in range(6)  # 超过限制(5)
        ]

        # 同时上传多个文件
        responses = []
        for file in files:
            response = self.client.post(reverse('converter:upload_session'), {
                'filename': file.name,
                'filesize': len(file.read()),
                'target_format': 'pdf'
            })
            file.seek(0)
            responses.append(response)

        # 验证只有前5个请求成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        self.assertEqual(success_count, 5)
        self.assertEqual(responses[-1].status_code, 429) 