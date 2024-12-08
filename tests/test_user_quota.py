"""用户配额测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.converter.models import ConversionTask
from apps.converter.quota import QuotaManager
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class UserQuotaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.quota_manager = QuotaManager()

    def test_quota_tracking(self):
        """测试配额跟踪"""
        # 初始配额
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 10)
        
        # 创建转换任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            target_format='pdf',
            file_size=1024 * 1024  # 1MB
        )
        
        # 检查配额更新
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 9)
        
        # 完成任务
        task.status = 'completed'
        task.save()
        
        # 验证配额统计
        usage = self.quota_manager.get_usage_stats(self.user)
        self.assertEqual(usage['total_conversions'], 1)
        self.assertEqual(usage['total_size'], 1024 * 1024)

    def test_quota_reset(self):
        """测试配额重置"""
        # 创建一些历史任务
        for _ in range(5):
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                target_format='pdf',
                status='completed',
                created_at=timezone.now() - timedelta(days=31)  # 上个月的任务
            )
            
        # 重置配额
        self.quota_manager.reset_quota(self.user)
        
        # 验证配额已重置
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 10)
        
        # 验证历史记录保留
        self.assertEqual(
            ConversionTask.objects.filter(user=self.user).count(),
            5
        )

    def test_quota_upgrade(self):
        """测试配额升级"""
        # 升级用户配额
        self.user.quota_plan = 'premium'
        self.user.save()
        
        # 验证新配额
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 100)
        
        # 验证高级功能
        self.assertTrue(self.quota_manager.can_use_priority_queue(self.user))
        self.assertTrue(self.quota_manager.can_use_batch_conversion(self.user))

    def test_concurrent_quota_usage(self):
        """测试并发配额使用"""
        import threading
        
        def create_task():
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                target_format='pdf',
                file_size=1024 * 1024
            )
            
        # 创建多个线程同时使用配额
        threads = [
            threading.Thread(target=create_task)
            for _ in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # 验证配额正确扣除
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 5)

    def test_quota_alerts(self):
        """测试配额警告"""
        # 使用大部分配额
        for _ in range(8):
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                target_format='pdf',
                status='completed'
            )
            
        # 检查警告
        alerts = self.quota_manager.get_quota_alerts(self.user)
        self.assertTrue(any(
            alert['type'] == 'quota_low'
            for alert in alerts
        ))
        
        # 验证通知发送
        self.assertTrue(
            self.quota_manager.should_notify_user(self.user)
        )

    def tearDown(self):
        # 清理测试数据
        ConversionTask.objects.all().delete() 