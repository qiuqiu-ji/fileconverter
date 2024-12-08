"""安全相关测试"""
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.security.validators import FileValidator, SecurityScanner
from django.core.exceptions import ValidationError
import os

User = get_user_model()

class FileValidationTest(TestCase):
    def setUp(self):
        self.validator = FileValidator()
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        os.makedirs(self.test_files_dir, exist_ok=True)

    def create_test_file(self, name, content, size=1024):
        """创建测试文件"""
        path = os.path.join(self.test_files_dir, name)
        with open(path, 'wb') as f:
            f.write(content * size)
        return SimpleUploadedFile(name, content * size)

    def test_valid_file(self):
        """测试有效文件"""
        file = self.create_test_file('test.txt', b'hello')
        try:
            FileValidator.validate_file(file)
        except ValidationError:
            self.fail('FileValidator raised ValidationError unexpectedly')

    def test_file_size_too_large(self):
        """测试文件大小超限"""
        large_file = self.create_test_file('large.txt', b'x', 1024 * 1024 * 11)  # 11MB
        with self.assertRaises(ValidationError):
            FileValidator.validate_file(large_file)

    def test_invalid_file_type(self):
        """测试无效文件类型"""
        exe_file = self.create_test_file('test.exe', b'MZ')
        with self.assertRaises(ValidationError):
            FileValidator.validate_file(exe_file)

class SecurityScannerTest(TestCase):
    def setUp(self):
        self.scanner = SecurityScanner()
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        os.makedirs(self.test_files_dir, exist_ok=True)

    def create_test_file(self, name, content):
        """创建测试文件"""
        path = os.path.join(self.test_files_dir, name)
        with open(path, 'wb') as f:
            f.write(content)
        return SimpleUploadedFile(name, content)

    def test_safe_file(self):
        """测试安全文件"""
        file = self.create_test_file('safe.txt', b'Hello, World!')
        try:
            SecurityScanner.scan_file(file)
        except ValidationError:
            self.fail('SecurityScanner raised ValidationError unexpectedly')

    def test_php_file(self):
        """测试PHP文件"""
        file = self.create_test_file('test.php', b'<?php echo "hello"; ?>')
        with self.assertRaises(ValidationError):
            SecurityScanner.scan_file(file)

    def test_executable_file(self):
        """测试可执行文件"""
        file = self.create_test_file('test.exe', b'MZ')
        with self.assertRaises(ValidationError):
            SecurityScanner.scan_file(file)

    def test_dangerous_filename(self):
        """测试危险文件名"""
        dangerous_names = [
            'test.php',
            'test.asp',
            'test.jsp',
            'test.cgi',
            'test.exe',
            'test.sh',
            'test.bat',
            'test;.txt',
            '../test.txt',
            '.htaccess'
        ]
        
        for name in dangerous_names:
            with self.assertRaises(ValidationError):
                SecurityScanner.check_filename(name)

class SecurityMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        self.upload_url = reverse('converter:upload')

    def test_rate_limit(self):
        """测试速率限制"""
        file = SimpleUploadedFile('test.txt', b'hello')
        
        # 发送大量请求
        for _ in range(101):  # 超过限制(100)
            response = self.client.post(self.upload_url, {'file': file})
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            self.fail('Rate limit not enforced')

    def test_concurrent_uploads(self):
        """测试并发上传限制"""
        files = [
            SimpleUploadedFile(f'test{i}.txt', b'hello')
            for i in range(21)  # 超过限制(20)
        ]
        
        response = self.client.post(self.upload_url, {'files': files})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Too many files', response.json()['error'])

    def test_total_size_limit(self):
        """测试总大小限制"""
        large_file = SimpleUploadedFile(
            'large.txt',
            b'x' * (1024 * 1024 * 101)  # 101MB, 超过限制(100MB)
        )
        
        response = self.client.post(self.upload_url, {'file': large_file})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Total size exceeds limit', response.json()['error'])

    def test_security_headers(self):
        """测试安全响应头"""
        response = self.client.get('/')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
        self.assertTrue(response['Strict-Transport-Security']) 