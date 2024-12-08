"""安全相关信号处理"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import SecurityLog, SecurityAlert

@receiver(post_save, sender=SecurityLog)
def handle_security_log(sender, instance, created, **kwargs):
    """处理安全日志"""
    if created and instance.level in ['ERROR', 'WARNING']:
        # 检查是否需要创建告警
        threshold = getattr(settings, 'SECURITY_ALERT_THRESHOLD', 3)
        cache_key = f'security_log_{instance.level}_{instance.message}'
        
        # 增加计数
        count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, count, timeout=3600)  # 1小时过期
        
        if count >= threshold:
            # 创建安全告警
            SecurityAlert.objects.create(
                title=f'Repeated {instance.level} Events',
                description=f'Event "{instance.message}" occurred {count} times in the last hour',
                severity='HIGH' if instance.level == 'ERROR' else 'MEDIUM',
                source='Security Log Monitor'
            )
            # 重置计数
            cache.delete(cache_key)

@receiver(post_save, sender=SecurityAlert)
def handle_security_alert(sender, instance, created, **kwargs):
    """处理安全告警"""
    if created and instance.severity in ['HIGH', 'CRITICAL']:
        # 这里可以添加通知管理员的逻辑
        from django.core.mail import send_mail
        from django.conf import settings
        
        send_mail(
            subject=f'Security Alert: {instance.title}',
            message=instance.description,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin[1] for admin in settings.ADMINS],
            fail_silently=True
        ) 