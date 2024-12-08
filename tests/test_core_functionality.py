"""核心功能测试套件"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from apps.converter.models import ConversionTask
from apps.security.models import SecurityLog
import os
import json

User = get_user_model()

class CoreFunctionalityTest(TestCase):
    """核心功能测试"""
    
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # 创建测试文件
        self.test_file = SimpleUploadedFile(
            "test.txt",
            b"Test file content",
            content_type="text/plain"
        )

    def test_file_upload_and_conversion(self):
        """测试文件上传和转换"""
        # 1. 上传文件
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('task_id', data)
        
        # 2. 检查任务创建
        task = ConversionTask.objects.get(id=data['task_id'])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'pending')
        
        # 3. 检查文件保存
        self.assertTrue(os.path.exists(task.original_file.path))
        
        # 4. 检查安全日志
        log = SecurityLog.objects.latest('created_at')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, 'file_upload')

    def test_file_validation(self):
        """测试文件验证"""
        # 1. 文件大小限制
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (settings.FILE_UPLOAD_MAX_MEMORY_SIZE + 1)
        )
        response = self.client.post(reverse('converter:upload'), {
            'file': large_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 400)
        
        # 2. 文件类型限制
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b"Invalid content",
            content_type="application/x-msdownload"
        )
        response = self.client.post(reverse('converter:upload'), {
            'file': invalid_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 400)

    def test_quota_management(self):
        """测试配额管理"""
        # 1. 设置用户配额
        self.user.conversion_quota = 2
        self.user.save()
        
        # 2. 使用配额
        for i in range(3):
            response = self.client.post(reverse('converter:upload'), {
                'file': SimpleUploadedFile(
                    f"test{i}.txt",
                    b"Test content",
                    content_type="text/plain"
                ),
                'target_format': 'pdf'
            })
            if i < 2:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 403)

    def test_task_management(self):
        """测试任务管理"""
        # 1. 创建任务
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        task_id = json.loads(response.content)['task_id']
        
        # 2. 检查状态
        response = self.client.get(reverse('converter:status', args=[task_id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. 重试失败任务
        task = ConversionTask.objects.get(id=task_id)
        task.status = 'failed'
        task.save()
        
        response = self.client.post(reverse('converter:retry', args=[task_id]))
        self.assertEqual(response.status_code, 200)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'pending')

    def test_security_features(self):
        """测试安全功能"""
        # 1. 频率限制
        for i in range(settings.FILE_UPLOAD_MAX_REQUESTS_PER_HOUR + 1):
            response = self.client.post(reverse('converter:upload'), {
                'file': self.test_file,
                'target_format': 'pdf'
            })
            if i == settings.FILE_UPLOAD_MAX_REQUESTS_PER_HOUR:
                self.assertEqual(response.status_code, 429)
        
        # 2. 文件安全检查
        malicious_file = SimpleUploadedFile(
            "malicious.txt",
            b"<?php echo 'hack'; ?>",
            content_type="text/plain"
        )
        response = self.client.post(reverse('converter:upload'), {
            'file': malicious_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 400)

    def test_error_handling(self):
        """测试错误处理"""
        # 1. 无效的转换格式
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'invalid'
        })
        self.assertEqual(response.status_code, 400)
        
        # 2. 文件不存在
        response = self.client.get(reverse('converter:download', args=[999]))
        self.assertEqual(response.status_code, 404)
        
        # 3. 未认证访问
        self.client.logout()
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 302)  # 重定向到登录页面

    def test_batch_operations(self):
        """测试批量操作"""
        # 1. 批量上传
        files = [
            SimpleUploadedFile(f"test{i}.txt", b"content", content_type="text/plain")
            for i in range(3)
        ]
        
        response = self.client.post(reverse('converter:batch_upload'), {
            'files[]': files,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['task_ids']), 3)
        
        # 2. 批量删除
        response = self.client.post(reverse('converter:batch_delete'), {
            'task_ids': data['task_ids']
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConversionTask.objects.count(), 0)

    def test_conversion_progress_tracking(self):
        """测试转换进度跟踪"""
        from channels.testing import WebsocketCommunicator
        from apps.converter.consumers import ConversionConsumer
        import asyncio
        
        async def test_websocket():
            # 创建转换任务
            response = self.client.post(reverse('converter:upload'), {
                'file': self.test_file,
                'target_format': 'pdf'
            })
            task_id = json.loads(response.content)['task_id']
            
            # 创建WebSocket连接
            communicator = WebsocketCommunicator(
                ConversionConsumer.as_asgi(),
                f"/ws/conversion/{task_id}/"
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # 模拟进度更新
            task = ConversionTask.objects.get(id=task_id)
            task.progress = 50
            task.save()
            
            # 接收进度消息
            response = await communicator.receive_json_from()
            self.assertEqual(response['progress'], 50)
            
            # 完成任务
            task.status = 'completed'
            task.progress = 100
            task.save()
            
            # 接收完成消息
            response = await communicator.receive_json_from()
            self.assertEqual(response['status'], 'completed')
            
            await communicator.disconnect()
        
        # 运行异步测试
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_websocket())

    def test_async_task_execution(self):
        """测试异步任务执行"""
        from apps.converter.tasks import convert_file_task
        from unittest.mock import patch
        
        # 创建任务
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        task_id = json.loads(response.content)['task_id']
        
        # 模拟Celery任务执行
        with patch('apps.converter.tasks.convert_file') as mock_convert:
            # 执行任务
            convert_file_task.apply(args=[task_id])
            
            # 验证任务调用
            mock_convert.assert_called_once_with(task_id)
            
            # 检查任务状态更新
            task = ConversionTask.objects.get(id=task_id)
            self.assertEqual(task.status, 'processing')
            
            # 模拟转换完成
            task.status = 'completed'
            task.save()
            
            # 验证结果
            task.refresh_from_db()
            self.assertEqual(task.status, 'completed')

    def test_file_cleanup(self):
        """测试文件清理"""
        from django.utils import timezone
        from datetime import timedelta
        from apps.converter.tasks import cleanup_old_files
        
        # 创建过期任务
        old_task = ConversionTask.objects.create(
            user=self.user,
            original_file=self.test_file,
            created_at=timezone.now() - timedelta(days=8)  # 超过7天
        )
        old_file_path = old_task.original_file.path
        
        # 创建新任务
        new_task = ConversionTask.objects.create(
            user=self.user,
            original_file=self.test_file
        )
        new_file_path = new_task.original_file.path
        
        # 运行清理
        cleanup_old_files.apply()
        
        # 验证文件清理
        self.assertFalse(os.path.exists(old_file_path))
        self.assertTrue(os.path.exists(new_file_path))
        
        # 验证任务清理
        self.assertFalse(
            ConversionTask.objects.filter(id=old_task.id).exists()
        )
        self.assertTrue(
            ConversionTask.objects.filter(id=new_task.id).exists()
        )

    def test_cache_mechanism(self):
        """测试缓存机制"""
        from django.core.cache import cache
        from apps.converter.utils import get_task_progress
        
        # 创建任务
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        task_id = json.loads(response.content)['task_id']
        
        # 设置进度缓存
        cache.set(f'task_progress:{task_id}', 50)
        
        # 验证缓存命中
        progress = get_task_progress(task_id)
        self.assertEqual(progress, 50)
        
        # 清除缓存
        cache.delete(f'task_progress:{task_id}')
        
        # 验证缓存失效后从数据库读取
        task = ConversionTask.objects.get(id=task_id)
        task.progress = 75
        task.save()
        
        progress = get_task_progress(task_id)
        self.assertEqual(progress, 75)

    def test_concurrent_task_processing(self):
        """测试并发任务处理"""
        import threading
        import queue
        
        results = queue.Queue()
        task_count = 5
        
        def create_task():
            try:
                response = self.client.post(reverse('converter:upload'), {
                    'file': SimpleUploadedFile(
                        "test.txt",
                        b"Test content",
                        content_type="text/plain"
                    ),
                    'target_format': 'pdf'
                })
                results.put(('success', response.status_code))
            except Exception as e:
                results.put(('error', str(e)))
        
        # 创建多个线程同时提交任务
        threads = []
        for _ in range(task_count):
            t = threading.Thread(target=create_task)
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, _ = results.get()
            if status == 'success':
                success_count += 1
            else:
                error_count += 1
        
        self.assertEqual(success_count, task_count)
        self.assertEqual(error_count, 0)
        
        # 验证任务创建
        self.assertEqual(
            ConversionTask.objects.count(),
            task_count
        )

    def tearDown(self):
        # 清理测试文件
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