"""视图测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import ConversionTask, ConversionHistory
import json
import os

User = get_user_model()

class ConversionViewsTests(TestCase):
    """转换视图测试"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
    def test_upload_file(self):
        """测试文件上传"""
        # 创建测试文件
        file_content = b'test file content'
        test_file = SimpleUploadedFile(
            'test.jpg',
            file_content,
            content_type='image/jpeg'
        )
        
        response = self.client.post(reverse('upload_file'), {
            'file': test_file,
            'target_format': 'png'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('task_id' in data)
        
    def test_check_status(self):
        """测试状态检查"""
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_format='jpg',
            target_format='png',
            status='processing'
        )
        
        response = self.client.get(
            reverse('check_status', args=[task.id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'processing')
        
    def test_conversion_history(self):
        """测试转换历史"""
        # 创建测试历史记录
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
        
        response = self.client.get(reverse('conversion_history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'converter/history.html') 