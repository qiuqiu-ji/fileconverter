"""错误处理和恢复机制"""
import logging
import traceback
from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import ConversionTask, ErrorLog
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

class ConversionError(Exception):
    """转换错误基类"""
    def __init__(self, message, error_code=None, details=None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

class FileValidationError(ConversionError):
    """文件验证错误"""
    pass

class ConversionProcessError(ConversionError):
    """转换处理错误"""
    pass

class StorageError(ConversionError):
    """存储错误"""
    pass

def handle_conversion_errors(view_func):
    """转换错误处理装饰器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except FileValidationError as e:
            logger.log_error('validation_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'error_code': e.error_code or 'VALIDATION_ERROR',
                'message': str(e),
                'details': e.details
            }, status=400)
        except ConversionProcessError as e:
            logger.log_error('conversion_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'error_code': e.error_code or 'CONVERSION_ERROR',
                'message': str(e),
                'details': e.details
            }, status=500)
        except StorageError as e:
            logger.log_error('storage_error', str(e), e.details)
            return JsonResponse({
                'status': 'error',
                'error_code': e.error_code or 'STORAGE_ERROR',
                'message': str(e),
                'details': e.details
            }, status=500)
        except Exception as e:
            # 记录未预期的错误
            logger.log_error('unexpected_error', str(e), {
                'traceback': traceback.format_exc()
            })
            return JsonResponse({
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'message': '服务器内部错误'
            }, status=500)
    return wrapper

class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    @staticmethod
    def recover_failed_task(task_id):
        """恢复失败的任务"""
        try:
            with transaction.atomic():
                task = ConversionTask.objects.select_for_update().get(id=task_id)
                
                if task.status != 'failed':
                    raise ValueError('只能恢复失败的任务')
                
                # 重置任务状态
                task.status = 'pending'
                task.error_message = None
                task.retry_count = (task.retry_count or 0) + 1
                task.save()
                
                # 重新提交任务
                from .tasks import convert_file_task
                convert_file_task.delay(task_id)
                
                logger.logger.info(f'Task {task_id} has been recovered')
                return True
                
        except Exception as e:
            logger.log_error('recovery_error', str(e), {'task_id': task_id})
            raise

    @staticmethod
    def cleanup_failed_tasks():
        """清理失败的任务"""
        try:
            # 获取所有重试次数超过限制的失败任务
            failed_tasks = ConversionTask.objects.filter(
                status='failed',
                retry_count__gte=3  # 最大重试次数
            )
            
            for task in failed_tasks:
                # 清理相关文件
                if task.original_file:
                    task.original_file.delete()
                if task.converted_file:
                    task.converted_file.delete()
                    
                # 记录错误日志
                ErrorLog.objects.create(
                    task_id=task.id,
                    error_type='max_retries_exceeded',
                    error_message=task.error_message,
                    user=task.user
                )
                
                # 删除任务
                task.delete()
                
            return len(failed_tasks)
            
        except Exception as e:
            logger.log_error('cleanup_error', str(e))
            raise

    @staticmethod
    def get_error_statistics():
        """获取错误统计信息"""
        try:
            stats = ErrorLog.objects.values('error_type').annotate(
                count=Count('id'),
                latest=Max('created_at')
            ).order_by('-count')
            
            return list(stats)
            
        except Exception as e:
            logger.log_error('stats_error', str(e))
            raise

class TaskMonitor:
    """任务监控器"""
    
    @staticmethod
    def check_task_health(task_id):
        """检查任务健康状态"""
        try:
            task = ConversionTask.objects.get(id=task_id)
            
            # 检查任务是否卡住
            if task.status == 'processing':
                time_limit = timezone.now() - timedelta(minutes=30)
                if task.updated_at < time_limit:
                    # 任务可能卡住了
                    logger.log_error('task_stuck', f'Task {task_id} appears to be stuck', {
                        'status': task.status,
                        'started_at': task.created_at,
                        'last_update': task.updated_at
                    })
                    return False
                    
            return True
            
        except Exception as e:
            logger.log_error('health_check_error', str(e), {'task_id': task_id})
            raise

    @staticmethod
    def get_task_metrics():
        """获取任务指标"""
        try:
            return {
                'total_tasks': ConversionTask.objects.count(),
                'failed_tasks': ConversionTask.objects.filter(status='failed').count(),
                'processing_tasks': ConversionTask.objects.filter(status='processing').count(),
                'avg_processing_time': ConversionTask.objects.filter(
                    status='completed'
                ).aggregate(
                    avg_time=Avg(F('updated_at') - F('created_at'))
                )['avg_time']
            }
        except Exception as e:
            logger.log_error('metrics_error', str(e))
            raise 