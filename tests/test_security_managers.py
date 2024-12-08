"""安全管理器测试"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.security.models import BlockedIP, AuditLog
from datetime import timedelta
import json

User = get_user_model()

class BlockedIPManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_block_ip(self):
        """测试IP封禁"""
        # 临时封禁
        blocked = BlockedIP.objects.block_ip(
            '192.168.1.1',
            'Test blocking',
            duration=24,
            blocked_by=self.user
        )
        self.assertFalse(blocked.is_permanent)
        self.assertTrue(blocked.is_active)
        self.assertEqual(blocked.reason, 'Test blocking')
        self.assertEqual(blocked.blocked_by, self.user)
        
        # 永久封禁
        blocked = BlockedIP.objects.block_ip(
            '192.168.1.2',
            'Test permanent blocking',
            permanent=True,
            blocked_by=self.user
        )
        self.assertTrue(blocked.is_permanent)
        self.assertTrue(blocked.is_active)
        self.assertIsNone(blocked.expires_at)

    def test_is_blocked(self):
        """测试IP封禁状态���查"""
        # 创建封禁记录
        BlockedIP.objects.block_ip('192.168.1.1', 'Test blocking')
        
        # 检查封禁状态
        self.assertTrue(BlockedIP.objects.is_blocked('192.168.1.1'))
        self.assertFalse(BlockedIP.objects.is_blocked('192.168.1.2'))
        
        # 检查缓存
        from django.core.cache import cache
        self.assertTrue(cache.get('blocked_ip:192.168.1.1'))

    def test_unblock_ip(self):
        """测试解除IP封禁"""
        # 创建封禁记录
        BlockedIP.objects.block_ip('192.168.1.1', 'Test blocking')
        
        # 解除封禁
        BlockedIP.objects.unblock_ip('192.168.1.1')
        
        # 验证结果
        self.assertFalse(BlockedIP.objects.is_blocked('192.168.1.1'))
        self.assertFalse(BlockedIP.objects.filter(ip_address='192.168.1.1').exists())

    def test_cleanup_expired(self):
        """测试清理过期封禁"""
        # 创建过期记录
        BlockedIP.objects.create(
            ip_address='192.168.1.1',
            reason='Test blocking',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # 创建有效记录
        BlockedIP.objects.block_ip('192.168.1.2', 'Test blocking')
        BlockedIP.objects.block_ip('192.168.1.3', 'Test permanent', permanent=True)
        
        # 清理过期记录
        deleted_count = BlockedIP.objects.cleanup_expired()[0]
        self.assertEqual(deleted_count, 1)
        self.assertEqual(BlockedIP.objects.count(), 2)

    def test_get_active_blocks(self):
        """测试获取活动封禁"""
        # 创建各种状态的封禁
        BlockedIP.objects.create(
            ip_address='192.168.1.1',
            reason='Expired block',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        BlockedIP.objects.block_ip('192.168.1.2', 'Active block')
        BlockedIP.objects.block_ip('192.168.1.3', 'Permanent block', permanent=True)
        
        # 获取活动封禁
        active_blocks = BlockedIP.objects.get_active_blocks()
        self.assertEqual(active_blocks.count(), 2)
        self.assertIn('192.168.1.2', [b.ip_address for b in active_blocks])
        self.assertIn('192.168.1.3', [b.ip_address for b in active_blocks])

class AuditLogManagerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_get_user_actions(self):
        """测试获取用户操作记录"""
        # 创建测试日志
        AuditLog.objects.create(
            user=self.user,
            action_type='login',
            action_detail='User login',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        # 创建其他用户的日志
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )
        AuditLog.objects.create(
            user=other_user,
            action_type='login',
            action_detail='Other user login',
            ip_address='192.168.1.2',
            user_agent='Mozilla/5.0'
        )
        
        # 获取用户操作记录
        logs = AuditLog.objects.get_user_actions(self.user)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs[0].action_type, 'login')
        self.assertEqual(logs[0].user, self.user)

    def test_get_resource_history(self):
        """测试获取资源操作历史"""
        # 创建资源操作日志
        AuditLog.objects.create(
            user=self.user,
            action_type='file_upload',
            action_detail='File uploaded',
            ip_address='192.168.1.1',
            resource_type='file',
            resource_id='123',
            extra_data={'size': 1024}
        )
        
        # 获取资源历史
        logs = AuditLog.objects.get_resource_history('file', '123')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs[0].resource_type, 'file')
        self.assertEqual(logs[0].resource_id, '123')
        self.assertEqual(logs[0].extra_data['size'], 1024)

    def test_get_security_events(self):
        """测试获取安全事件"""
        # 创建不同级别的事件
        AuditLog.objects.create(
            action_type='login',
            action_detail='Failed login attempt',
            severity='warning',
            ip_address='192.168.1.1'
        )
        AuditLog.objects.create(
            action_type='file_upload',
            action_detail='Malicious file detected',
            severity='critical',
            ip_address='192.168.1.1'
        )
        
        # 获取严重事件
        critical_events = AuditLog.objects.get_security_events(severity='critical')
        self.assertEqual(critical_events.count(), 1)
        self.assertEqual(critical_events[0].severity, 'critical')

    def test_get_ip_history(self):
        """测试获取IP操作历史"""
        # 创建IP操作日志
        AuditLog.objects.create(
            user=self.user,
            action_type='login',
            action_detail='Login from IP',
            ip_address='192.168.1.1'
        )
        AuditLog.objects.create(
            user=self.user,
            action_type='file_upload',
            action_detail='Upload from IP',
            ip_address='192.168.1.1'
        )
        
        # 获取IP历史
        logs = AuditLog.objects.get_ip_history('192.168.1.1')
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs[0].ip_address, '192.168.1.1')

    def test_cleanup_old_logs(self):
        """测试清理旧日志"""
        # 创建旧日志
        old_log = AuditLog.objects.create(
            action_type='login',
            action_detail='Old login',
            ip_address='192.168.1.1'
        )
        old_log.created_at = timezone.now() - timedelta(days=100)
        old_log.save()
        
        # 创建新日志
        AuditLog.objects.create(
            action_type='login',
            action_detail='Recent login',
            ip_address='192.168.1.1'
        )
        
        # 清理旧日志
        deleted_count = AuditLog.objects.cleanup_old_logs(days=90)[0]
        self.assertEqual(deleted_count, 1)
        self.assertEqual(AuditLog.objects.count(), 1) 