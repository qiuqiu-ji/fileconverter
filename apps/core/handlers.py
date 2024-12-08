"""错误处理器"""
import logging
import traceback
from django.conf import settings
from django.core.mail import mail_admins
from django.utils.translation import gettext as _

logger = logging.getLogger('apps.core')

class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_error(request, exception, error_id=None):
        """处理错误"""
        # 获取错误信息
        error_info = {
            'error_id': error_id,
            'url': request.build_absolute_uri(),
            'method': request.method,
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
            'ip': request.META.get('REMOTE_ADDR'),
            'exception': str(exception),
            'traceback': traceback.format_exc()
        }
        
        # 记录错误日志
        logger.error(
            f"Error ID: {error_id}\n"
            f"URL: {error_info['url']}\n"
            f"Method: {error_info['method']}\n"
            f"User: {error_info['user']}\n"
            f"IP: {error_info['ip']}\n"
            f"Exception: {error_info['exception']}\n"
            f"Traceback:\n{error_info['traceback']}"
        )
        
        # 发送错误通知
        if not settings.DEBUG:
            ErrorHandler.send_error_notification(error_info)
        
        return error_info

    @staticmethod
    def send_error_notification(error_info):
        """发送错误通知"""
        subject = f"[{settings.SITE_NAME}] Error: {error_info['exception'][:50]}"
        message = (
            f"Error ID: {error_info['error_id']}\n"
            f"URL: {error_info['url']}\n"
            f"Method: {error_info['method']}\n"
            f"User: {error_info['user']}\n"
            f"IP: {error_info['ip']}\n"
            f"Exception: {error_info['exception']}\n"
            f"\nTraceback:\n{error_info['traceback']}"
        )
        
        try:
            mail_admins(subject, message, fail_silently=True)
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")

    @staticmethod
    def get_error_message(exception, default_message=None):
        """获取错误消息"""
        if hasattr(exception, 'message'):
            return str(exception.message)
        elif default_message:
            return default_message
        else:
            return _('An unexpected error occurred') 

    def handle_batch_errors(self, errors):
        """批量处理错误"""
        from django.db import transaction
        from apps.core.monitoring import ErrorMonitor
        
        results = {
            'processed': 0,
            'failed': 0,
            'notifications_sent': 0
        }
        
        with transaction.atomic():
            for error in errors:
                try:
                    # 处理单个错误
                    error_info = self.handle_error(error['request'], error['exception'])
                    
                    # 记录错误统计
                    ErrorMonitor.record_error(error_info)
                    
                    results['processed'] += 1
                    
                    # 检查是否需要发送通知
                    if self._should_send_notification(error_info):
                        self.send_error_notification(error_info)
                        results['notifications_sent'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process error: {str(e)}")
                    results['failed'] += 1
        
        return results

    def cleanup_old_errors(self, days=30, batch_size=1000):
        """清理旧错误记录"""
        from django.utils import timezone
        from datetime import timedelta
        from apps.security.models import SecurityLog
        
        cutoff_date = timezone.now() - timedelta(days=days)
        total_deleted = 0
        
        try:
            # 分批删除旧记录
            while True:
                ids = SecurityLog.objects.filter(
                    created_at__lt=cutoff_date
                ).values_list('id', flat=True)[:batch_size]
                
                if not ids:
                    break
                    
                deleted_count = SecurityLog.objects.filter(id__in=ids).delete()[0]
                total_deleted += deleted_count
                
                logger.info(f"Deleted {deleted_count} old error records")
                
        except Exception as e:
            logger.error(f"Error cleaning up old errors: {str(e)}")
            raise
        
        return total_deleted

    def _should_send_notification(self, error_info):
        """检查是否应该发送通知"""
        from django.conf import settings
        from django.core.cache import cache
        
        # 获取通知设置
        notification_settings = getattr(settings, 'ERROR_NOTIFICATION_SETTINGS', {})
        if not notification_settings.get('email_enabled'):
            return False
        
        # 检查错误频率
        threshold = notification_settings.get('notification_threshold', 10)
        window = notification_settings.get('aggregation_window', 3600)
        
        cache_key = f"error_notification:{error_info['exception']}"
        count = cache.get(cache_key, 0)
        
        if count == 0:
            cache.set(cache_key, 1, timeout=window)
            return True
        
        cache.incr(cache_key)
        return count % threshold == 0 