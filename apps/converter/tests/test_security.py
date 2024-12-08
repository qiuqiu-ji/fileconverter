"""安全功能测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.security.validators import FileValidator, SecurityScanner
from apps.security.logging import FileConverterLogger
from django.core.exceptions import ValidationError
import os

User = get_user_model()

class SecurityValidatorTests(TestCase):
    """安全验证测试"""
    
    def setUp(self):
        self.validator = FileValidator()
        
    def test_file_size_validation(self):
        """测试文件大小验证"""
        # 创建超大文件
        large_file = SimpleUploadedFile(
            "large.jpg",
            b"x" * (11 * 1024 * 1024)  # 11MB
        )
        
        with self.assertRaises(ValidationError):
            self.validator.validate_file(large_file)
            
    def test_file_type_validation(self):
        """测试文件类型验证"""
        # 创建可执行文件
        exe_file = SimpleUploadedFile(
            "test.exe",
            b"dangerous content",
            content_type="application/x-msdownload"
        )
        
        with self.assertRaises(ValidationError):
            self.validator.validate_file(exe_file)
            
    def test_filename_validation(self):
        """测试文件名验证"""
        dangerous_names = [
            "../etc/passwd",
            "shell.php;.jpg",
            "../../config.php",
            "%00hidden.jpg"
        ]
        
        for name in dangerous_names:
            with self.assertRaises(ValidationError):
                SecurityScanner.check_filename(name)

class SecurityScannerTests(TestCase):
    """安全扫描测试"""
    
    def setUp(self):
        self.scanner = SecurityScanner()
        
    def test_malware_scan(self):
        """测试恶意软件扫描"""
        # 创建测试文件
        malware_pattern = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        test_file = SimpleUploadedFile(
            "test.txt",
            malware_pattern
        )
        
        with self.assertRaises(ValidationError):
            self.scanner.scan_file(test_file)
            
    def test_content_validation(self):
        """测试文件内容验证"""
        # 创建包含PHP代码的图片文件
        php_code = b"<?php system($_GET['cmd']); ?>"
        fake_image = b"GIF89a" + php_code
        
        test_file = SimpleUploadedFile(
            "image.gif",
            fake_image,
            content_type="image/gif"
        )
        
        with self.assertRaises(ValidationError):
            self.scanner.scan_file(test_file)

class LoggingTests(TestCase):
    """日志记录测试"""
    
    def setUp(self):
        self.logger = FileConverterLogger()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_conversion_logging(self):
        """测试转换日志记录"""
        self.logger.log_conversion_start(
            task_id='123',
            user=self.user,
            original_format='jpg',
            target_format='png'
        )
        
        # 验证日志文件是否存在并包含正确信息
        log_file = self.logger.logger.handlers[0].baseFilename
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn('conversion_start', content)
            self.assertIn('123', content)
            self.assertIn('testuser', content)
            
    def test_error_logging(self):
        """测试错误日志记录"""
        error_message = "Test error message"
        self.logger.log_error(
            'test_error',
            error_message,
            {'extra': 'info'}
        )
        
        # 验证错误日志
        log_file = self.logger.logger.handlers[0].baseFilename
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn('test_error', content)
            self.assertIn(error_message, content)
            self.assertIn('extra', content) 