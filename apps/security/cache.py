"""缓存管理"""
from django.core.cache import cache
from django.conf import settings
import json
from datetime import timedelta

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.cache = cache
        self.default_timeout = 3600  # 1小时
        
    def get_conversion_result(self, task_id):
        """获取转换结果缓存"""
        cache_key = f'conversion_result:{task_id}'
        return self.cache.get(cache_key)
        
    def set_conversion_result(self, task_id, result, timeout=None):
        """设置转换结果缓存"""
        cache_key = f'conversion_result:{task_id}'
        self.cache.set(
            cache_key,
            result,
            timeout or self.default_timeout
        )
        
    def get_upload_session(self, session_id):
        """获取上传会话缓存"""
        cache_key = f'upload_session:{session_id}'
        return self.cache.get(cache_key)
        
    def set_upload_session(self, session_id, data, timeout=None):
        """设置上传会话缓存"""
        cache_key = f'upload_session:{session_id}'
        self.cache.set(
            cache_key,
            data,
            timeout or self.default_timeout
        )
        
    def delete_upload_session(self, session_id):
        """删除上传会话缓存"""
        cache_key = f'upload_session:{session_id}'
        self.cache.delete(cache_key)
        
    def increment_request_count(self, ip_address):
        """增加请求计数"""
        cache_key = f'request_count:{ip_address}'
        try:
            return self.cache.incr(cache_key)
        except ValueError:
            self.cache.set(cache_key, 1, 60)  # 1分钟过期
            return 1
            
    def get_request_count(self, ip_address):
        """获取请求计数"""
        cache_key = f'request_count:{ip_address}'
        return self.cache.get(cache_key, 0)
        
    def clear_request_count(self, ip_address):
        """清除请求计数"""
        cache_key = f'request_count:{ip_address}'
        self.cache.delete(cache_key)
        
    def set_rate_limit(self, identifier, limit, timeout):
        """设置速率限制"""
        cache_key = f'rate_limit:{identifier}'
        self.cache.set(cache_key, limit, timeout)
        
    def check_rate_limit(self, identifier):
        """检查速率限制"""
        cache_key = f'rate_limit:{identifier}'
        return self.cache.get(cache_key, 0)