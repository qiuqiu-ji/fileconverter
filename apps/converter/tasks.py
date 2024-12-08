from celery import shared_task
from django.core.cache import cache
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ConversionTask
from .converter import FileConverter
import os
import time
import logging
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from functools import wraps

logger = logging.getLogger(__name__)

def retry_on_error(max_retries=3, delay=60):
    """错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.error(
                        f"Task failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
            raise last_error
        return wrapper
    return decorator

@shared_task
@retry_on_error()
def convert_file(self, task_id):
    """文件转换任务"""
    channel_layer = get_channel_layer()
    task = ConversionTask.objects.get(id=task_id)
    converter = FileConverter()
    
    try:
        # 更新任务状态
        task.status = 'processing'
        task.started_at = timezone.now()
        task.save()
        
        # 设置初始进度
        cache.set(f'task_progress:{task_id}', 0)
        _notify_progress(channel_layer, task_id, 0, 'started')
        
        # 验证文件大小
        total_size = os.path.getsize(task.original_file.path)
        if total_size > settings.CONVERSION_SETTINGS['max_file_size']:
            raise ValueError("File too large")
        
        # 分块处理大文件
        chunk_size = settings.CONVERSION_SETTINGS['chunk_size']
        processed_size = 0
        
        with open(task.original_file.path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                    
                try:
                    # 处理数据块
                    converter.process_chunk(chunk)
                    
                    # 更新进度
                    processed_size += len(chunk)
                    progress = int((processed_size / total_size) * 100)
                    cache.set(f'task_progress:{task_id}', progress)
                    _notify_progress(channel_layer, task_id, progress, 'processing')
                    
                    # 防止CPU过载
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}")
                    # 重试当前块
                    time.sleep(1)
                    continue
        
        # 完成转换
        output_path = converter.complete_conversion(task.target_format)
        
        # 保存结果
        with open(output_path, 'rb') as f:
            task.output_file.save(
                f"{task.id}.{task.target_format}",
                f
            )
        
        # 更新任务状态
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # 清理缓存和临时文件
        cache.delete(f'task_progress:{task_id}')
        _cleanup_temp_files(output_path)
        
        # 发送完成通知
        _notify_progress(channel_layer, task_id, 100, 'completed')
        
    except Exception as e:
        logger.exception(f"Conversion failed for task {task_id}: {str(e)}")
        
        # 更新任务状态
        task.status = 'failed'
        task.error_message = str(e)
        task.save()
        
        # 发送错误通知
        _notify_progress(channel_layer, task_id, 0, 'failed', str(e))
        
        # 重试任务
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        raise

def _notify_progress(channel_layer, task_id, progress, status, message=None):
    """发送进度通知"""
    try:
        async_to_sync(channel_layer.group_send)(
            f'task_{task_id}',
            {
                'type': 'conversion_progress',
                'task_id': task_id,
                'progress': progress,
                'status': status,
                'message': message
            }
        )
    except Exception as e:
        logger.error(f"Failed to send progress notification: {str(e)}")

def _cleanup_temp_files(*paths):
    """清理临时文件"""
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {path}: {str(e)}")

@shared_task
def cleanup_old_files():
    """清理过期文件(添加错误处理)"""
    logger = logging.getLogger(__name__)
    
    try:
        with transaction.atomic():
            # 获取过期任务
            expired_tasks = ConversionTask.objects.filter(
                created_at__lt=timezone.now() - timedelta(days=7)
            ).select_for_update()
            
            deleted_count = 0
            error_count = 0
            
            for task in expired_tasks:
                try:
                    # 删除文件
                    if task.original_file:
                        task.original_file.delete(save=False)
                    if task.output_file:
                        task.output_file.delete(save=False)
                    deleted_count += 1
                except OSError as e:
                    logger.error(f"Failed to delete files for task {task.id}: {e}")
                    error_count += 1
                    continue
            
            # 删除任务记录
            expired_tasks.delete()
            
            logger.info(
                f"Cleanup completed: {deleted_count} tasks deleted, "
                f"{error_count} errors occurred"
            )
            
    except Exception as e:
        logger.error(f"File cleanup failed: {e}")
        raise