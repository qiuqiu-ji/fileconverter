import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from apps.converter.models import ConversionTask
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

class FileCleanupService:
    """文件清理服务"""
    
    @staticmethod
    def cleanup_old_files(days=7):
        """清理指定天数之前的文件"""
        try:
            # 计算截止日期
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 获取需要清理的任务
            old_tasks = ConversionTask.objects.filter(
                created_at__lt=cutoff_date,
                status__in=['completed', 'failed']
            )
            
            deleted_count = 0
            for task in old_tasks:
                try:
                    # 删除原始文件
                    if task.original_file:
                        if default_storage.exists(task.original_file.name):
                            default_storage.delete(task.original_file.name)
                    
                    # 删除转换后的文件
                    if task.converted_file:
                        if default_storage.exists(task.converted_file.name):
                            default_storage.delete(task.converted_file.name)
                    
                    # 更新任务状态
                    task.original_file = None
                    task.converted_file = None
                    task.save()
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.log_error('file_cleanup_error', str(e), {
                        'task_id': task.id,
                        'original_file': task.original_file.name if task.original_file else None,
                        'converted_file': task.converted_file.name if task.converted_file else None
                    })
            
            logger.logger.info(f'Cleaned up {deleted_count} old files')
            return deleted_count
            
        except Exception as e:
            logger.log_error('file_cleanup_error', str(e))
            raise

    @staticmethod
    def cleanup_temp_files():
        """清理临时文件"""
        try:
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            if os.path.exists(temp_dir):
                deleted_count = 0
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            # 检查文件是否超过24小时
                            if datetime.fromtimestamp(os.path.getctime(file_path)) < datetime.now() - timedelta(days=1):
                                os.remove(file_path)
                                deleted_count += 1
                        except Exception as e:
                            logger.log_error('temp_file_cleanup_error', str(e), {'file_path': file_path})
                    
                    # 删除空目录
                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            if not os.listdir(dir_path):
                                os.rmdir(dir_path)
                        except Exception as e:
                            logger.log_error('temp_dir_cleanup_error', str(e), {'dir_path': dir_path})
                
                logger.logger.info(f'Cleaned up {deleted_count} temporary files')
                return deleted_count
                
        except Exception as e:
            logger.log_error('temp_cleanup_error', str(e))
            raise 