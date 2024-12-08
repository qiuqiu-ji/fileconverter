"""性能和并发测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask
from concurrent.futures import ThreadPoolExecutor
import time
import threading

User = get_user_model()

class PerformanceTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_concurrent_uploads(self):
        """测试并发上传"""
        num_threads = 5
        results = []
        
        def upload_file():
            file = SimpleUploadedFile(
                f"test_{threading.get_ident()}.txt",
                b"Test content",
                content_type="text/plain"
            )
            response = self.client.post(reverse('converter:upload_session'), {
                'filename': file.name,
                'filesize': len(file.read()),
                'target_format': 'pdf'
            })
            file.seek(0)
            return response.status_code

        # 使用线程池并发上传
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(upload_file) for _ in range(num_threads)]
            results = [f.result() for f in futures]

        # 验证结果
        success_count = sum(1 for status in results if status == 200)
        self.assertEqual(success_count, num_threads)

    def test_conversion_performance(self):
        """测试转换性能"""
        # 创建大文件
        large_content = b"Test content\n" * 1000
        large_file = SimpleUploadedFile(
            "large.txt",
            large_content,
            content_type="text/plain"
        )

        # 记录开始时间
        start_time = time.time()

        # 上传并转换
        response = self.client.post(reverse('converter:upload_session'), {
            'filename': large_file.name,
            'filesize': len(large_file.read()),
            'target_format': 'pdf'
        })
        large_file.seek(0)

        self.assertEqual(response.status_code, 200)
        session_data = response.json()

        # 等待转换完成
        task_id = session_data['task_id']
        max_wait = 30  # 最大等待时间（秒）
        while time.time() - start_time < max_wait:
            task = ConversionTask.objects.get(id=task_id)
            if task.status in ['completed', 'failed']:
                break
            time.sleep(1)

        # 验证性能
        conversion_time = time.time() - start_time
        self.assertLess(conversion_time, max_wait)
        self.assertEqual(task.status, 'completed')

    def test_memory_usage(self):
        """测试内存使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行一系列操作
        for i in range(10):
            file = SimpleUploadedFile(
                f"test_{i}.txt",
                b"Test content" * 100,
                content_type="text/plain"
            )
            response = self.client.post(reverse('converter:upload_session'), {
                'filename': file.name,
                'filesize': len(file.read()),
                'target_format': 'pdf'
            })
            file.seek(0)
            self.assertEqual(response.status_code, 200)

        # 检查内存增长
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 确保内存增长在合理范围内（例如小于100MB）
        self.assertLess(memory_increase, 100 * 1024 * 1024)

    def test_database_performance(self):
        """测试数据库性能"""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # 创建测试数据
        for i in range(100):
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf'
            )

        # 测试列表查询性能
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(reverse('converter:history'))
            self.assertEqual(response.status_code, 200)

        # 验证查询数量在合理范围内
        query_count = len(context)
        self.assertLess(query_count, 10)  # 应该使用select_related/prefetch_related优化 