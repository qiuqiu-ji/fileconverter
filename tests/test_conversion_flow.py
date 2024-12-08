"""文件转换流程测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.converter.models import ConversionTask
from apps.converter.tasks import convert_file
import os
import time

User = get_user_model()

class ConversionFlowTest(TestCase):
    def setUp(self):
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
        """测试完整的文件转换流程"""
        # 1. 上传文件
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        task_id = response.json()['task_id']
        
        # 2. 验证任务创建
        task = ConversionTask.objects.get(id=task_id)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.user, self.user)
        
        # 3. 执行转换
        convert_file(task_id)
        task.refresh_from_db()
        
        # 4. 检查结果
        self.assertEqual(task.status, 'completed')
        self.assertTrue(os.path.exists(task.output_file.path))
        
        # 5. 下载文件
        response = self.client.get(reverse('converter:download', args=[task_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_batch_conversion(self):
        """测试批量转换"""
        # 创建多个测试文件
        files = [
            SimpleUploadedFile(
                f"test{i}.txt",
                f"Test content {i}".encode(),
                content_type="text/plain"
            )
            for i in range(3)
        ]
        
        # 批量上传
        response = self.client.post(reverse('converter:batch_upload'), {
            'files[]': files,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 200)
        task_ids = response.json()['task_ids']
        
        # 执行转换
        for task_id in task_ids:
            convert_file(task_id)
            
        # 验证结果
        tasks = ConversionTask.objects.filter(id__in=task_ids)
        self.assertEqual(tasks.count(), 3)
        self.assertTrue(all(task.status == 'completed' for task in tasks))

    def test_conversion_progress(self):
        """测试转换进度跟踪"""
        # 创建大文件以便观察进度
        large_content = b"x" * (1024 * 1024)  # 1MB
        large_file = SimpleUploadedFile(
            "large.txt",
            large_content,
            content_type="text/plain"
        )
        
        # 上传文件
        response = self.client.post(reverse('converter:upload'), {
            'file': large_file,
            'target_format': 'pdf'
        })
        task_id = response.json()['task_id']
        
        # 启动转换
        convert_file.delay(task_id)
        
        # 检查进度
        progress = 0
        for _ in range(10):  # 最多等待10秒
            response = self.client.get(reverse('converter:progress', args=[task_id]))
            progress = response.json()['progress']
            if progress == 100:
                break
            time.sleep(1)
            
        self.assertEqual(progress, 100)

    def test_error_handling(self):
        """测试错误处理"""
        # 创建无效文件
        invalid_file = SimpleUploadedFile(
            "test.xyz",
            b"Invalid content",
            content_type="application/octet-stream"
        )
        
        # 尝试上传
        response = self.client.post(reverse('converter:upload'), {
            'file': invalid_file,
            'target_format': 'pdf'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        
        # 尝试无效转换
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=self.test_file.name,
            target_format='invalid'
        )
        convert_file(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')

    def test_quota_limits(self):
        """测试配额限制"""
        # 设置用户配额
        self.user.conversion_quota = 2
        self.user.save()
        
        # 尝试超出配额
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
                self.assertIn('quota exceeded', response.json()['error'])

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