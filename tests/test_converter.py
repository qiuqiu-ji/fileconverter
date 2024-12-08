"""转换器相关测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask
from apps.converter.tasks import convert_file
import os
import shutil
import tempfile

User = get_user_model()

class FileConversionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def create_test_file(self, name, content):
        """创建测试文件"""
        path = os.path.join(self.temp_dir, name)
        with open(path, 'wb') as f:
            f.write(content)
        return SimpleUploadedFile(name, content)

    def test_upload_file(self):
        """测试文件上传"""
        file = self.create_test_file('test.txt', b'Hello, World!')
        response = self.client.post(reverse('converter:upload'), {'file': file})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('task_id', data)
        
        # 检查任务是否创建
        task = ConversionTask.objects.get(id=data['task_id'])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.original_format, 'txt')
        self.assertEqual(task.status, 'pending')

    def test_convert_txt_to_pdf(self):
        """测试TXT转PDF"""
        # 创建转换任务
        file = self.create_test_file('test.txt', b'Hello, World!')
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=file,
            original_format='txt',
            target_format='pdf'
        )
        
        # 执行转换
        convert_file(task.id)
        task.refresh_from_db()
        
        # 检查结果
        self.assertEqual(task.status, 'completed')
        self.assertTrue(task.converted_file)
        self.assertTrue(os.path.exists(task.converted_file.path))
        self.assertTrue(task.converted_file.name.endswith('.pdf'))

    def test_convert_invalid_format(self):
        """测试无效格式转换"""
        file = self.create_test_file('test.xyz', b'Invalid format')
        response = self.client.post(reverse('converter:upload'), {
            'file': file,
            'target_format': 'pdf'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported format', response.json()['error'])

    def test_conversion_limit(self):
        """测试转换限制"""
        # 设置用户的转换限制
        self.user.daily_conversion_limit = 2
        self.user.save()
        
        # 创建多个转换任务
        for i in range(3):
            file = self.create_test_file(f'test{i}.txt', b'Hello')
            response = self.client.post(reverse('converter:upload'), {'file': file})
            
            if i < 2:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 429)
                self.assertIn('Daily limit exceeded', response.json()['error'])

    def test_storage_quota(self):
        """测试存储配额"""
        # 设置用户的存储配额
        self.user.storage_quota = 1024  # 1KB
        self.user.save()
        
        # 尝试上传大文件
        file = self.create_test_file('large.txt', b'x' * 2048)  # 2KB
        response = self.client.post(reverse('converter:upload'), {'file': file})
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Storage quota exceeded', response.json()['error'])

class BatchConversionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def test_batch_upload(self):
        """测试批量上传"""
        files = [
            SimpleUploadedFile(f'test{i}.txt', b'Hello')
            for i in range(3)
        ]
        
        response = self.client.post(reverse('converter:batch_upload'), {
            'files[]': files,
            'target_format': 'pdf'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('batch_id', data)
        self.assertEqual(len(data['tasks']), 3)

    def test_batch_conversion(self):
        """测试批量转换"""
        # 创建批量任务
        files = [
            SimpleUploadedFile(f'test{i}.txt', b'Hello')
            for i in range(3)
        ]
        
        response = self.client.post(reverse('converter:batch_upload'), {
            'files[]': files,
            'target_format': 'pdf'
        })
        
        batch_id = response.json()['batch_id']
        
        # 检查任务状态
        response = self.client.get(reverse('converter:batch_status', args=[batch_id]))
        data = response.json()
        
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['completed'], 0)
        self.assertEqual(data['status'], 'processing')

    def test_batch_limit(self):
        """测试批量限制"""
        files = [
            SimpleUploadedFile(f'test{i}.txt', b'Hello')
            for i in range(21)  # 超过限制(20)
        ]
        
        response = self.client.post(reverse('converter:batch_upload'), {
            'files[]': files,
            'target_format': 'pdf'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Too many files', response.json()['error'])

class ConversionHistoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_history_page(self):
        """测试历史记录页面"""
        response = self.client.get(reverse('converter:history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'converter/history.html')

    def test_history_list(self):
        """测试历史记录列表"""
        # 创建一些转换任务
        for i in range(5):
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status='completed'
            )
        
        response = self.client.get(reverse('converter:history'))
        self.assertEqual(len(response.context['history_items']), 5)

    def test_delete_history(self):
        """测试删除历史记录"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='completed'
        )
        
        response = self.client.post(reverse('converter:delete_history', args=[task.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConversionTask.objects.filter(id=task.id).exists()) 