"""系统集成测试"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from channels.testing import WebsocketCommunicator
from apps.converter.models import (
    ConversionTask, 
    ConversionHistory,
    ConversionStatistics
)
from apps.converter.consumers import ConversionConsumer
from apps.security.models import SecurityLog
import os
import json
import asyncio
import threading
from datetime import timedelta

User = get_user_model()

class SystemIntegrationTest(TransactionTestCase):
    """系统集成测试"""
    
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # 创建测试文件
        self.test_file = SimpleUploadedFile(
            "test.txt",
            b"Test file content",
            content_type="text/plain"
        )

    def test_complete_conversion_flow(self):
        """测试完整转换流程"""
        # 1. 文件上传
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        task_id = json.loads(response.content)['task_id']
        
        # 2. 任务创建验证
        task = ConversionTask.objects.get(id=task_id)
        self.assertEqual(task.status, 'pending')
        
        # 3. 转换进度跟踪
        async def track_progress():
            communicator = WebsocketCommunicator(
                ConversionConsumer.as_asgi(),
                f"/ws/conversion/{task_id}/"
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # 模拟进度更新
            task.progress = 50
            task.save()
            
            response = await communicator.receive_json_from()
            self.assertEqual(response['progress'], 50)
            
            await communicator.disconnect()
            
        asyncio.run(track_progress())
        
        # 4. 转换完成
        task.status = 'completed'
        task.save()
        
        # 5. 验证历史记录
        history = ConversionHistory.objects.get(task=task)
        self.assertEqual(history.user, self.user)
        
        # 6. 验证统计数据
        stats = ConversionStatistics.objects.latest('created_at')
        self.assertGreater(stats.task_count, 0)

    def test_concurrent_system_load(self):
        """测试系统并发负载"""
        def run_conversion():
            response = self.client.post(reverse('converter:upload'), {
                'file': SimpleUploadedFile(
                    "test.txt",
                    b"Test content",
                    content_type="text/plain"
                ),
                'target_format': 'pdf'
            })
            return response.status_code == 200
            
        # 创建多个线程同时执行转换
        threads = []
        results = []
        for _ in range(10):  # 10个并发请求
            t = threading.Thread(
                target=lambda: results.append(run_conversion())
            )
            threads.append(t)
            t.start()
            
        # 等待所有线程完成
        for t in threads:
            t.join()
            
        # 验证所有请求都成功
        self.assertTrue(all(results))
        
        # 验证系统状态
        self.assertLess(
            ConversionStatistics.objects.latest('created_at').cpu_usage,
            90  # CPU使用率不应超过90%
        )

    def test_error_recovery(self):
        """测试错误恢复"""
        # 1. 创建失败的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=self.test_file,
            target_format='pdf',
            status='failed',
            error_message='Test error'
        )
        
        # 2. 尝试重试
        response = self.client.post(
            reverse('converter:retry_task', args=[task.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. 验证任务状态重置
        task.refresh_from_db()
        self.assertEqual(task.status, 'pending')
        
        # 4. 验证错误日志
        self.assertTrue(
            SecurityLog.objects.filter(
                action_type='task_retry',
                user=self.user
            ).exists()
        )

    def test_system_cleanup(self):
        """测试系统清理"""
        # 1. 创建过期任务
        old_task = ConversionTask.objects.create(
            user=self.user,
            original_file=self.test_file,
            created_at=timezone.now() - timedelta(days=8)
        )
        
        # 2. 创建过期会话
        from apps.converter.models import UploadSession
        old_session = UploadSession.objects.create(
            user=self.user,
            session_id='test',
            filename='test.txt',
            file_size=1000,
            chunk_size=100,
            total_chunks=10,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # 3. 运行清理
        from apps.converter.tasks import cleanup_old_files
        cleanup_old_files.apply()
        
        # 4. 验证清理结果
        self.assertFalse(
            ConversionTask.objects.filter(id=old_task.id).exists()
        )
        self.assertFalse(
            UploadSession.objects.filter(id=old_session.id).exists()
        )

    def test_system_monitoring(self):
        """测试系统监控"""
        # 1. 创建一些负载
        for _ in range(5):
            self.client.post(reverse('converter:upload'), {
                'file': self.test_file,
                'target_format': 'pdf'
            })
            
        # 2. 检查监控指标
        stats = ConversionStatistics.objects.latest('created_at')
        self.assertIsNotNone(stats.cpu_usage)
        self.assertIsNotNone(stats.memory_usage)
        self.assertIsNotNone(stats.response_time)
        
        # 3. 验证告警机制
        self.assertLess(stats.error_count, 3)  # 错误数应该较少

    def tearDown(self):
        # 清理测试文件和缓存
        for task in ConversionTask.objects.all():
            if task.original_file:
                try:
                    os.remove(task.original_file.path)
                except:
                    pass
            if task.output_file:
                try:
                    os.remove(task.output_file.path)
                except:
                    pass
        cache.clear() 