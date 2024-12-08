"""文件预览功能测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from apps.accounts.models import User
from apps.converter.models import ConversionTask
import json
import os

class FilePreviewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_preview(self):
        """测试文档预览"""
        # 上传文档文件
        doc_file = SimpleUploadedFile(
            "test.txt",
            b"Hello World! This is a test document.",
            content_type="text/plain"
        )

        # 创建转换任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=doc_file,
            original_format='txt',
            target_format='pdf',
            status='completed'
        )

        # 获取预览
        response = self.client.get(reverse('converter:preview', args=[task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_image_preview(self):
        """测试图片预览"""
        # 创建测试图片
        with open('tests/test_files/test.jpg', 'rb') as f:
            image_content = f.read()

        image_file = SimpleUploadedFile(
            "test.jpg",
            image_content,
            content_type="image/jpeg"
        )

        # 创建转换任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=image_file,
            original_format='jpg',
            target_format='png',
            status='completed'
        )

        # 获取预览
        response = self.client.get(reverse('converter:preview', args=[task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'] in ['image/jpeg', 'image/png'])

    def test_preview_generation(self):
        """测试预览生成"""
        # 上传大文档
        large_doc = SimpleUploadedFile(
            "large.txt",
            b"Content " * 1000,  # 较大的文本内容
            content_type="text/plain"
        )

        # 创建转换任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file=large_doc,
            original_format='txt',
            target_format='pdf',
            status='completed'
        )

        # 请求预览生成
        response = self.client.post(reverse('converter:preview', args=[task.id]))
        self.assertEqual(response.status_code, 202)  # Accepted
        data = json.loads(response.content)
        self.assertIn('preview_id', data)

        # 检查预览状态
        preview_id = data['preview_id']
        response = self.client.get(reverse('converter:preview_status', args=[preview_id]))
        self.assertEqual(response.status_code, 200)
        status_data = json.loads(response.content)
        self.assertIn('status', status_data)

    def test_invalid_preview_request(self):
        """测试无效的预览请求"""
        # 测试不存在的任务
        response = self.client.get(reverse('converter:preview', args=['invalid-id']))
        self.assertEqual(response.status_code, 404)

        # 测试未完成的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )
        response = self.client.get(reverse('converter:preview', args=[task.id]))
        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        # 清理测试文件
        for task in ConversionTask.objects.all():
            if task.original_file:
                try:
                    os.remove(task.original_file.path)
                except FileNotFoundError:
                    pass
            if task.converted_file:
                try:
                    os.remove(task.converted_file.path)
                except FileNotFoundError:
                    pass 