"""任务测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import ConversionTask
from ..tasks import convert_file_task
from unittest.mock import patch

User = get_user_model()

class ConversionTaskTests(TestCase):
    """转换任务测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    @patch('apps.converter.tasks.FileConverter.convert_file')
    def test_convert_file_task(self, mock_convert):
        """测试文件转换任务"""
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_format='jpg',
            target_format='png',
            status='pending'
        )
        
        # 执行任务
        result = convert_file_task(task.id)
        
        # 验证结果
        self.assertEqual(result['status'], 'completed')
        mock_convert.assert_called_once()
        
        # 检查任务状态
        task.refresh_from_db()
        self.assertEqual(task.status, 'completed') 