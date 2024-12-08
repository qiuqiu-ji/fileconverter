"""高级功能测试"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from apps.converter.models import (
    ConversionTask,
    PreviewTask,
    ConversionStatistics
)
import os
import json
import time
from PIL import Image
from io import BytesIO

User = get_user_model()

class AdvancedFeaturesTest(TransactionTestCase):
    """高级功能测试"""
    
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
        
        # 创建测试图片
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        self.test_image = SimpleUploadedFile(
            "test.jpg",
            img_io.getvalue(),
            content_type='image/jpeg'
        )

    def test_file_preview(self):
        """测试文件预览功能"""
        # 1. 上传文件
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_file,
            'target_format': 'pdf'
        })
        task_id = json.loads(response.content)['task_id']
        
        # 2. 请求预览
        response = self.client.post(reverse('converter:preview', args=[task_id]))
        self.assertEqual(response.status_code, 202)  # 异步生成预览
        preview_id = json.loads(response.content)['preview_id']
        
        # 3. 等待预览生成
        max_wait = 10  # 最多等待10秒
        while max_wait > 0:
            response = self.client.get(
                reverse('converter:preview_status', args=[preview_id])
            )
            if json.loads(response.content)['status'] == 'completed':
                break
            time.sleep(1)
            max_wait -= 1
        
        # 4. 获取预览
        response = self.client.get(
            reverse('converter:view_preview', args=[preview_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_custom_conversion_options(self):
        """测试自定义转换选项"""
        # 1. 图片转换选项
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_image,
            'target_format': 'png',
            'options': json.dumps({
                'quality': 'high',
                'dpi': 300,
                'resize': {'width': 800, 'height': 600}
            })
        })
        self.assertEqual(response.status_code, 200)
        task_id = json.loads(response.content)['task_id']
        
        # 2. 等待转换完成
        task = ConversionTask.objects.get(id=task_id)
        task.status = 'completed'
        task.save()
        
        # 3. 验证转换结果
        with Image.open(task.output_file.path) as img:
            self.assertEqual(img.size, (800, 600))
            self.assertEqual(img.format, 'PNG')

    def test_batch_download(self):
        """测试批量下载功能"""
        # 1. 创建多个转换任务
        task_ids = []
        for i in range(3):
            response = self.client.post(reverse('converter:upload'), {
                'file': SimpleUploadedFile(
                    f"test{i}.txt",
                    f"Content {i}".encode(),
                    content_type="text/plain"
                ),
                'target_format': 'pdf'
            })
            task_ids.append(json.loads(response.content)['task_id'])
        
        # 2. 标记任务完成
        for task_id in task_ids:
            task = ConversionTask.objects.get(id=task_id)
            task.status = 'completed'
            task.save()
        
        # 3. 请求批量下载
        response = self.client.post(reverse('converter:batch_download'), {
            'task_ids': task_ids
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/zip'
        )

    def test_large_file_handling(self):
        """测试大文件处理"""
        # 创建大文件(10MB)
        large_content = b"x" * (10 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            "large.txt",
            large_content,
            content_type="text/plain"
        )
        
        # 1. 测试分片上传
        session_response = self.client.post(
            reverse('converter:create_upload_session'),
            {
                'filename': 'large.txt',
                'filesize': len(large_content),
                'chunk_size': 1024 * 1024
            }
        )
        session_id = json.loads(session_response.content)['session_id']
        
        # 2. 上传分片
        chunk_size = 1024 * 1024
        for i in range(0, len(large_content), chunk_size):
            chunk = large_content[i:i + chunk_size]
            response = self.client.post(
                reverse('converter:upload_chunk'),
                {
                    'session_id': session_id,
                    'chunk_index': i // chunk_size,
                    'chunk': SimpleUploadedFile(
                        f"chunk_{i}.dat",
                        chunk
                    )
                }
            )
            self.assertEqual(response.status_code, 200)
        
        # 3. 完成上传
        complete_response = self.client.post(
            reverse('converter:complete_upload'),
            {'session_id': session_id}
        )
        self.assertEqual(complete_response.status_code, 200)
        
        # 4. 验证内存使用
        stats = ConversionStatistics.objects.latest('created_at')
        self.assertLess(stats.memory_usage, 512 * 1024 * 1024)  # 内存使用应小于512MB

    def test_format_conversion_quality(self):
        """测试格式转换质量"""
        # 1. 图片质量测试
        response = self.client.post(reverse('converter:upload'), {
            'file': self.test_image,
            'target_format': 'png',
            'options': json.dumps({
                'quality': 'high',
                'dpi': 300
            })
        })
        task_id = json.loads(response.content)['task_id']
        
        # 2. 等待转换完成
        task = ConversionTask.objects.get(id=task_id)
        task.status = 'completed'
        task.save()
        
        # 3. 验证图片质量
        with Image.open(task.output_file.path) as img:
            # 检查DPI
            self.assertEqual(img.info.get('dpi'), (300, 300))
            # 检查色彩深度
            self.assertEqual(img.mode, 'RGB')

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
        cache.clear() 