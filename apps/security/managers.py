"""安全管理器"""
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

class BlockedIPManager(models.Manager):
    """IP封禁管理器"""
    
    def is_blocked(self, ip_address):
        """检查IP是否被封禁"""
        # 先检查缓存
        cache_key = f'blocked_ip:{ip_address}'
        if cache.get(cache_key):
            return True
            
        # 检查数据库
        blocked = self.filter(
            ip_address=ip_address,
            is_permanent=True
        ).exists() or self.filter(
            ip_address=ip_address,
            expires_at__gt=timezone.now()
        ).exists()
        
        if blocked:
            # 缓存封禁状态
            cache.set(cache_key, True, timeout=300)  # 5分钟
            
        return blocked

    def block_ip(self, ip_address, reason, duration=24, permanent=False, blocked_by=None):
        """封禁IP"""
        expires_at = None if permanent else timezone.now() + timedelta(hours=duration)
        
        blocked_ip, created = self.update_or_create(
            ip_address=ip_address,
            defaults={
                'reason': reason,
                'expires_at': expires_at,
                'is_permanent': permanent,
                'blocked_by': blocked_by
            }
        )
        
        # 更新缓存
        cache_key = f'blocked_ip:{ip_address}'
        cache.set(cache_key, True, timeout=300)
        
        return blocked_ip

    def unblock_ip(self, ip_address):
        """解除IP封禁"""
        self.filter(ip_address=ip_address).delete()
        cache_key = f'blocked_ip:{ip_address}'
        cache.delete(cache_key)

    def cleanup_expired(self):
        """清理过期的封禁记录"""
        return self.filter(
            is_permanent=False,
            expires_at__lt=timezone.now()
        ).delete()

    def get_active_blocks(self):
        """获取当前有效的封禁"""
        return self.filter(
            models.Q(is_permanent=True) |
            models.Q(expires_at__gt=timezone.now())
        ).order_by('-blocked_at')

class AuditLogManager(models.Manager):
    """审计日志管理器"""
    
    def get_user_actions(self, user, days=7):
        """获取用户操作记录"""
        return self.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=days)
        ).order_by('-created_at')

    def get_resource_history(self, resource_type, resource_id):
        """获取资源操作历史"""
        return self.filter(
            resource_type=resource_type,
            resource_id=resource_id
        ).order_by('-created_at')

    def get_security_events(self, severity=None, days=1):
        """获取安全事件"""
        queryset = self.filter(
            created_at__gte=timezone.now() - timedelta(days=days)
        )
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset.order_by('-created_at')

    def get_ip_history(self, ip_address, days=7):
        """获取IP操作历史"""
        return self.filter(
            ip_address=ip_address,
            created_at__gte=timezone.now() - timedelta(days=days)
        ).order_by('-created_at')

    def cleanup_old_logs(self, days=90):
        """清理旧日志"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__lt=cutoff_date).delete() 