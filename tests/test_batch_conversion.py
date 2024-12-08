"""批量转换测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from apps.accounts.models import User
from apps.converter.models import BatchConversionTask, ConversionTask
import json

class BatchConversionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        
        # 创建多个测试文件
        self.test_files = [
            SimpleUploadedFile(
                f"test{i}.txt",
                f"Test content {i}".encode(),
                content_type="text/plain"
            ) for i in range(3)
        ]

    def test_batch_conversion(self):
        """测试批量转换功能"""
        # 1. 创建批量转换任务
        response = self.client.post(reverse('converter:batch_create'), {
            'target_format': 'pdf',
            'file_count': len(self.test_files)
        })
        self.assertEqual(response.status_code, 200)
        batch_data = json.loads(response.content)
        batch_id = batch_data['batch_id']
        
        # 2. 上传多个文件
        for i, file in enumerate(self.test_files):
            response = self.client.post(reverse('converter:batch_upload'), {
                'batch_id': batch_id,
                'file': file,
                'file_number': i + 1
            })
            self.assertEqual(response.status_code, 200)
        
        # 3. 开始批量转换
        response = self.client.post(reverse('converter:batch_start'), {
            'batch_id': batch_id
        })
        self.assertEqual(response.status_code, 200)
        
        # 4. 检查所有任务状态
        batch_task = BatchConversionTask.objects.get(id=batch_id)
        self.assertEqual(batch_task.total_files, len(self.test_files))
        self.assertEqual(batch_task.completed_files, len(self.test_files))
        
        for task in ConversionTask.objects.filter(batch=batch_task):
            self.assertEqual(task.status, 'completed')
            self.assertTrue(task.converted_file.name.endswith('.pdf')) 