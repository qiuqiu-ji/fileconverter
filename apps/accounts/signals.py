"""用户信号处理器"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import User, UserProfile
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """创建用户时自动创建用户配置文件"""
    if created:
        UserProfile.objects.create(user=instance)
        logger.log_audit(
            'user_created',
            instance,
            {'email': instance.email}
        )

@receiver(pre_save, sender=User)
def update_user_status(sender, instance, **kwargs):
    """更新用户状态时记录日志"""
    if instance.pk:  # 已存在的用户
        try:
            old_instance = User.objects.get(pk=instance.pk)
            # 检查状态变化
            if old_instance.is_active != instance.is_active:
                logger.log_audit(
                    'user_status_changed',
                    instance,
                    {
                        'old_status': old_instance.is_active,
                        'new_status': instance.is_active,
                        'timestamp': timezone.now()
                    }
                )
            # 检查验证状态变化
            if old_instance.is_verified != instance.is_verified:
                logger.log_audit(
                    'user_verification_changed',
                    instance,
                    {
                        'old_status': old_instance.is_verified,
                        'new_status': instance.is_verified,
                        'timestamp': timezone.now()
                    }
                )
        except User.DoesNotExist:
            pass

@receiver(post_save, sender=UserProfile)
def handle_profile_update(sender, instance, created, **kwargs):
    """处理用户配置文件更新"""
    if not created:
        # 记录配置文件更新
        logger.log_audit(
            'profile_updated',
            instance.user,
            {
                'language': instance.language,
                'timezone': instance.timezone,
                'email_notifications': instance.email_notifications,
                'conversion_notifications': instance.conversion_notifications,
                'timestamp': timezone.now()
            }
        )
        
        # 检查头像更新
        if instance.tracker.has_changed('avatar'):
            logger.log_audit(
                'avatar_updated',
                instance.user,
                {
                    'timestamp': timezone.now()
                }
            )

@receiver(pre_save, sender=User)
def track_user_changes(sender, instance, **kwargs):
    """跟踪用户变化"""
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            changes = {}
            
            # 检查配额变化
            if old_instance.daily_conversion_limit != instance.daily_conversion_limit:
                changes['daily_conversion_limit'] = {
                    'old': old_instance.daily_conversion_limit,
                    'new': instance.daily_conversion_limit
                }
            
            if old_instance.storage_quota != instance.storage_quota:
                changes['storage_quota'] = {
                    'old': old_instance.storage_quota,
                    'new': instance.storage_quota
                }
            
            # 如果有变化，记录日志
            if changes:
                logger.log_audit(
                    'user_quota_changed',
                    instance,
                    {
                        'changes': changes,
                        'timestamp': timezone.now()
                    }
                )
                
        except User.DoesNotExist:
            pass

@receiver(post_save, sender=User)
def handle_user_login(sender, instance, **kwargs):
    """处理用户登录"""
    if instance.tracker.has_changed('last_login_at'):
        logger.log_audit(
            'user_login',
            instance,
            {
                'timestamp': instance.last_login_at,
                'ip_address': instance.last_login_ip
            }
        )

@receiver(post_save, sender=User)
def handle_password_change(sender, instance, **kwargs):
    """处理密码修改"""
    if instance.tracker.has_changed('password'):
        logger.log_audit(
            'password_changed',
            instance,
            {
                'timestamp': timezone.now()
            }
        )