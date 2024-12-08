"""转换工具类"""
from django.core.cache import cache
import time
import logging
from .models import ConversionTask

logger = logging.getLogger(__name__)

def get_task_progress(task_id):
    """获取任务进度(添加重试机制)"""
    # 尝试从缓存获取
    progress = cache.get(f'task_progress:{task_id}')
    if progress is not None:
        return progress
    
    # 缓存未命中，从数据库读取
    retry_count = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(retry_count):
        try:
            task = ConversionTask.objects.get(id=task_id)
            progress = task.progress
            
            # 更新缓存
            cache.set(f'task_progress:{task_id}', progress, 300)  # 5分钟
            return progress
            
        except ConversionTask.DoesNotExist:
            return None
            
        except Exception as e:
            logger.warning(
                f"Failed to get task progress (attempt {attempt + 1}): {e}"
            )
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # ���数退避
                continue
            raise
    
    return None

def invalidate_task_cache(task_id):
    """清除任务缓存"""
    cache_keys = [
        f'task_progress:{task_id}',
        f'task_status:{task_id}',
        f'task_result:{task_id}'
    ]
    
    for key in cache_keys:
        try:
            cache.delete(key)
        except Exception as e:
            logger.error(f"Failed to invalidate cache key {key}: {e}")

def get_task_status(task_id):
    """获取任务状态(带缓存)"""
    # 尝试从缓存获取
    status = cache.get(f'task_status:{task_id}')
    if status is not None:
        return status
        
    try:
        task = ConversionTask.objects.get(id=task_id)
        status = task.status
        
        # 更新缓存
        cache.set(f'task_status:{task_id}', status, 300)
        return status
        
    except ConversionTask.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return None

def update_task_progress(task_id, progress):
    """更新任务进度(带缓存)"""
    try:
        task = ConversionTask.objects.get(id=task_id)
        task.update_progress(progress)
        
        # 更新缓存
        cache.set(f'task_progress:{task_id}', progress, 300)
        return True
        
    except Exception as e:
        logger.error(f"Failed to update task progress: {e}")
        return False