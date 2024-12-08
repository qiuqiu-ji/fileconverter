"""安全日志管理"""
import logging
import json
from datetime import datetime
from django.conf import settings
import os

class FileConverterLogger:
    """文件转换日志管理器"""
    
    def __init__(self):
        # 创建日志目录
        self.log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 配置主日志记录器
        self.logger = self._setup_logger(
            'file_converter',
            os.path.join(self.log_dir, 'file_converter.log')
        )
        
        # 配置安全日志记录器
        self.security_logger = self._setup_logger(
            'security',
            os.path.join(self.log_dir, 'security.log')
        )
        
        # 配置审计日志记录器
        self.audit_logger = self._setup_logger(
            'audit',
            os.path.join(self.log_dir, 'audit.log')
        )

    def _setup_logger(self, name, log_file):
        """配置日志记录器"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(handler)
        
        return logger

    def log_conversion_start(self, task_id, user, original_format, target_format):
        """记录转换开始"""
        self.logger.info(
            'Conversion started',
            extra={
                'task_id': task_id,
                'user_id': user.id,
                'username': user.username,
                'original_format': original_format,
                'target_format': target_format,
                'timestamp': datetime.now().isoformat()
            }
        )

    def log_conversion_complete(self, task_id, success, error=None):
        """记录转换完成"""
        self.logger.info(
            'Conversion completed',
            extra={
                'task_id': task_id,
                'success': success,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )

    def log_security_event(self, event_type, details, user=None):
        """记��安全事件"""
        event_data = {
            'event_type': event_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'ip_address': details.get('ip_address'),
            'user_agent': details.get('user_agent')
        }
        
        if user:
            event_data.update({
                'user_id': user.id,
                'username': user.username
            })
            
        self.security_logger.warning(json.dumps(event_data))

    def log_audit(self, action, user, details):
        """记录审计信息"""
        audit_data = {
            'action': action,
            'user_id': user.id,
            'username': user.username,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_logger.info(json.dumps(audit_data))

    def log_error(self, error_type, message, details=None):
        """记录错误信息"""
        error_data = {
            'error_type': error_type,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.error(json.dumps(error_data))

    def log_success(self, task):
        """记录成功转换"""
        success_data = {
            'task_id': task.id,
            'user_id': task.user.id,
            'original_format': task.original_format,
            'target_format': task.target_format,
            'processing_time': str(task.processing_time),
            'file_size': task.file_size,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(json.dumps(success_data))