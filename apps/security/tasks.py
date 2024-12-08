from celery import shared_task
from .cleaners import FileCleanupService
from .cache import CacheManager
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

@shared_task
def cleanup_old_files():
    """定时清理旧文件"""
    try:
        service = FileCleanupService()
        deleted_count = service.cleanup_old_files()
        logger.logger.info(f'Scheduled cleanup: removed {deleted_count} old files')
    except Exception as e:
        logger.log_error('scheduled_cleanup_error', str(e))

@shared_task
def cleanup_temp_files():
    """定时清理临时文件"""
    try:
        service = FileCleanupService()
        deleted_count = service.cleanup_temp_files()
        logger.logger.info(f'Scheduled temp cleanup: removed {deleted_count} temporary files')
    except Exception as e:
        logger.log_error('scheduled_temp_cleanup_error', str(e))

@shared_task
def clear_expired_cache():
    """定时清理过期缓存"""
    try:
        cache_manager = CacheManager()
        cache_manager.clear_expired_cache()
        logger.logger.info('Scheduled cache cleanup completed')
    except Exception as e:
        logger.log_error('scheduled_cache_cleanup_error', str(e)) 