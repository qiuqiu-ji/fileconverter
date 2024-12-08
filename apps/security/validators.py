"""安全验证器"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.conf import settings
import re
import magic

class FileValidator:
    """文件验证器"""
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.max_size = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
        self.allowed_types = settings.ALLOWED_FILE_TYPES

    def validate_file_type(self, file):
        """验证文件类型"""
        mime_type = self.mime.from_buffer(file.read(1024))
        file.seek(0)  # 重置文件指针
        
        extension = file.name.split('.')[-1].lower()
        if extension not in self.allowed_types:
            raise ValidationError(_('Unsupported file type'))
            
        if mime_type != self.allowed_types[extension]:
            raise ValidationError(_('File type does not match extension'))

    def validate_file_size(self, file):
        """验证文件大小"""
        if file.size > self.max_size:
            raise ValidationError(
                _('File size %(size)s exceeds limit of %(limit)s') % {
                    'size': self._format_size(file.size),
                    'limit': self._format_size(self.max_size)
                }
            )

    def _format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

class RateLimiter:
    """速率限制器"""
    def __init__(self, cache_key_prefix, max_requests, time_window):
        self.cache_key_prefix = cache_key_prefix
        self.max_requests = max_requests
        self.time_window = time_window

    def is_allowed(self, identifier):
        """检查是否允许请求"""
        cache_key = f"{self.cache_key_prefix}_{identifier}"
        
        # 获取当前计数
        count = cache.get(cache_key, 0)
        
        if count >= self.max_requests:
            return False
            
        # 增加计数
        if count == 0:
            cache.set(cache_key, 1, self.time_window)
        else:
            cache.incr(cache_key)
            
        return True

class SecurityScanner:
    """安全扫描器"""
    @staticmethod
    def scan_file(file):
        """扫描文件内容"""
        # 读取文件内容
        content = file.read()
        file.seek(0)
        
        # 检查恶意代码特征
        patterns = [
            rb'<script.*?>.*?</script>',  # JavaScript代码
            rb'eval\s*\(',  # eval函数
            rb'document\.cookie',  # Cookie操作
            rb'(?:exec|system|popen)\s*\(',  # 系统命令执行
            rb'(?:SELECT|INSERT|UPDATE|DELETE).*?FROM',  # SQL注入
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.I | re.S):
                raise ValidationError(_('File contains malicious code'))

    @staticmethod
    def check_filename(filename):
        """检查文件名安全性"""
        # 检查文件名长度
        if len(filename) > 255:
            raise ValidationError(_('Filename too long'))
            
        # 检查危险字符
        if re.search(r'[<>:"|?*\\\\/]', filename):
            raise ValidationError(_('Invalid filename'))
            
        # 检查路径遍历
        if '..' in filename or filename.startswith('/'):
            raise ValidationError(_('Invalid filename'))
            
        # 检查隐藏文件
        if filename.startswith('.'):
            raise ValidationError(_('Hidden files not allowed'))
            
        # 检查危险扩展名
        dangerous_extensions = {
            'php', 'jsp', 'asp', 'aspx', 'exe', 'dll',
            'sh', 'bat', 'cmd', 'vbs', 'ps1'
        }
        extension = filename.split('.')[-1].lower()
        if extension in dangerous_extensions:
            raise ValidationError(_('File type not allowed'))