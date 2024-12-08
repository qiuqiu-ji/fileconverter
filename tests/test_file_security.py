"""文件安全检查测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from apps.accounts.models import User
from apps.security.validators import FileValidator, SecurityScanner
from django.core.exceptions import ValidationError

class FileSecurityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        self.validator = FileValidator()
        self.scanner = SecurityScanner()

    def test_file_type_validation(self):
        """测试文件类型验证"""
        # 测试有效文件
        valid_file = SimpleUploadedFile(
            "test.txt",
            b"Hello World!",
            content_type="text/plain"
        )
        try:
            self.validator.validate_file_type(valid_file)
        except ValidationError:
            self.fail("Valid file raised ValidationError")

        # 测试无效文件类型
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b"MZ",
            content_type="application/x-msdownload"
        )
        with self.assertRaises(ValidationError):
            self.validator.validate_file_type(invalid_file)

    def test_file_content_scanning(self):
        """测试文件内容扫描"""
        # 测试正常文件
        safe_file = SimpleUploadedFile(
            "safe.txt",
            b"Safe content",
            content_type="text/plain"
        )
        try:
            self.scanner.scan_file(safe_file)
        except ValidationError:
            self.fail("Safe file raised ValidationError")

        # 测试包含恶意代码的文件
        malicious_file = SimpleUploadedFile(
            "malicious.php",
            b"<?php system($_GET['cmd']); ?>",
            content_type="text/plain"
        )
        with self.assertRaises(ValidationError):
            self.scanner.scan_file(malicious_file)

    def test_filename_validation(self):
        """测试文件名验证"""
        # 测试正常文件名
        self.validator.validate_filename("normal.txt")

        # 测试危险文件名
        dangerous_names = [
            "../etc/passwd",
            "file;.txt",
            ".htaccess",
            "cmd.exe",
            "script.php"
        ]
        for name in dangerous_names:
            with self.assertRaises(ValidationError):
                self.validator.validate_filename(name) 