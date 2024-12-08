"""配额管理"""
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class QuotaManager:
    """配额管理器"""
    
    def __init__(self):
        self.settings = settings.QUOTA_SETTINGS
        self.quota_plans = self.settings['plans']
        self.alert_thresholds = self.settings['alert_thresholds']
    
    def check_quota(self, user, file_size):
        """检查配额"""
        cache_key = f'quota_check:{user.id}'
        lock_key = f'quota_lock:{user.id}'
        
        try:
            with cache.lock(lock_key, timeout=5):
                # 检查文件大小限制
                if file_size > self.settings['max_file_size']:
                    return False, 'File size exceeds limit'
                
                # 检查剩余配额
                remaining = self.get_remaining_quota(user)
                if remaining <= 0:
                    return False, 'Quota exceeded'
                
                # 检查总使用量
                total_usage = self.get_total_usage(user)
                if total_usage + file_size > self.settings['max_total_size']:
                    return False, 'Total storage limit exceeded'
                
                return True, None
                
        except Exception as e:
            logger.error(f"Failed to check quota: {str(e)}")
            return False, 'Quota check failed'
    
    def use_quota(self, user, file_size):
        """使用配额"""
        cache_key = f'user_quota:{user.id}'
        lock_key = f'quota_lock:{user.id}'
        
        try:
            with cache.lock(lock_key, timeout=5):
                with transaction.atomic():
                    # 更新用户配额
                    user.used_quota += 1
                    user.used_storage += file_size
                    user.save()
                    
                    # 更新缓存
                    cache.delete(cache_key)
                    
                    # 检查是否需要发送警告
                    self._check_quota_alerts(user)
                    
                return True
                
        except Exception as e:
            logger.error(f"Failed to use quota: {str(e)}")
            return False
    
    def get_remaining_quota(self, user):
        """获取剩余配额"""
        cache_key = f'user_quota:{user.id}'
        remaining = cache.get(cache_key)
        
        if remaining is None:
            plan = self.quota_plans.get(user.quota_plan, self.quota_plans['free'])
            remaining = max(0, plan['conversions'] - user.used_quota)
            cache.set(cache_key, remaining, self.settings['cache_timeout'])
            
        return remaining
    
    def get_total_usage(self, user):
        """获取总使用量"""
        cache_key = f'storage_usage:{user.id}'
        usage = cache.get(cache_key)
        
        if usage is None:
            usage = user.used_storage
            cache.set(cache_key, usage, self.settings['cache_timeout'])
            
        return usage
    
    def reset_quota(self, user):
        """重置配额"""
        with transaction.atomic():
            user.used_quota = 0
            user.last_reset = timezone.now()
            user.save()
            
            # 清除缓存
            cache.delete(f'user_quota:{user.id}')
            cache.delete(f'storage_usage:{user.id}')
    
    def _check_quota_alerts(self, user):
        """检查配额警告"""
        remaining = self.get_remaining_quota(user)
        plan = self.quota_plans.get(user.quota_plan, self.quota_plans['free'])
        ratio = remaining / plan['conversions']
        
        # 检查是否需要发送警告
        if ratio <= self.alert_thresholds['critical']:
            self._send_quota_alert(user, 'critical', remaining)
        elif ratio <= self.alert_thresholds['low']:
            self._send_quota_alert(user, 'warning', remaining)
    
    def _send_quota_alert(self, user, level, remaining):
        """发送配额警告"""
        from django.core.mail import send_mail
        
        # 检查通知冷却时间
        cache_key = f'quota_alert:{user.id}:{level}'
        if cache.get(cache_key):
            return
            
        try:
            send_mail(
                f'Quota Alert: {level.title()}',
                f'You have {remaining} conversions remaining.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True
            )
            
            # 设置通知冷却时间
            cache.set(cache_key, True, self.settings['notification_cooldown'])
            
        except Exception as e:
            logger.error(f"Failed to send quota alert: {str(e)}") 