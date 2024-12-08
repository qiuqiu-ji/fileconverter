"""配额管理测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from apps.converter.quota import QuotaManager
from apps.converter.models import ConversionTask
import threading
import time
from django.utils import timezone
from django.db import transaction

User = get_user_model()

class QuotaManagementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.quota_manager = QuotaManager()

    def test_plan_features(self):
        """测试不同计划的功能"""
        # 测试免费版功能
        self.user.quota_plan = 'free'
        self.user.save()
        
        # 检查文件大小限制
        result, message = self.quota_manager.check_quota(
            self.user,
            20 * 1024 * 1024  # 20MB
        )
        self.assertFalse(result)
        self.assertIn('size exceeds limit', message)
        
        # 测试基础版功能
        self.user.quota_plan = 'basic'
        self.user.save()
        
        result, message = self.quota_manager.check_quota(
            self.user,
            20 * 1024 * 1024  # 20MB
        )
        self.assertTrue(result)
        
        # 测试高级版功能
        self.user.quota_plan = 'premium'
        self.user.save()
        
        result, message = self.quota_manager.check_quota(
            self.user,
            90 * 1024 * 1024  # 90MB
        )
        self.assertTrue(result)

    def test_concurrent_quota_usage(self):
        """测试并发配额使用"""
        def use_quota():
            self.quota_manager.use_quota(
                self.user,
                1024 * 1024  # 1MB
            )
            
        # 创建多个线程同时使用配额
        threads = []
        for _ in range(5):
            t = threading.Thread(target=use_quota)
            threads.append(t)
            
        # 启动所有线程
        for t in threads:
            t.start()
            
        # 等待所有线程完成
        for t in threads:
            t.join()
            
        # 验证配额使用正确
        self.assertEqual(self.user.used_quota, 5)
        self.assertEqual(
            self.user.used_storage,
            5 * 1024 * 1024
        )

    def test_quota_reset(self):
        """测试配额重置"""
        # 用一些配额
        self.quota_manager.use_quota(
            self.user,
            1024 * 1024  # 1MB
        )
        
        # 重置配额
        self.quota_manager.reset_quota(self.user)
        
        # 验证重置结果
        self.assertEqual(self.user.used_quota, 0)
        self.assertIsNotNone(self.user.last_reset)
        
        # 验证缓存已清除
        self.assertIsNone(
            cache.get(f'user_quota:{self.user.id}')
        )

    def test_quota_alerts(self):
        """测试配额警告"""
        # 使用大部分配额
        plan = settings.QUOTA_SETTINGS['plans']['free']
        for _ in range(8):  # 使用80%配额
            self.quota_manager.use_quota(
                self.user,
                1024 * 1024
            )
            
        # 检查是否触发警告
        self.quota_manager._check_quota_alerts(self.user)
        
        # 验证警告邮件
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Quota Alert', mail.outbox[0].subject)

    def test_storage_limits(self):
        """测试存储限制"""
        # 尝试超出存储限制
        result, message = self.quota_manager.check_quota(
            self.user,
            2 * 1024 * 1024 * 1024  # 2GB
        )
        self.assertFalse(result)
        self.assertIn('storage limit exceeded', message)

    def test_quota_cache(self):
        """测试配额缓存"""
        # 首次获取配额（会查询数据库）
        quota1 = self.quota_manager.get_remaining_quota(self.user)
        
        # 修改数据库中的值
        self.user.used_quota += 1
        self.user.save()
        
        # 再次获取配额（应该返回缓存的值）
        quota2 = self.quota_manager.get_remaining_quota(self.user)
        
        # 验证返回缓存的值
        self.assertEqual(quota1, quota2)
        
        # 清除缓存
        cache.delete(f'user_quota:{self.user.id}')
        
        # 再次获取配额（应该返回新值）
        quota3 = self.quota_manager.get_remaining_quota(self.user)
        self.assertEqual(quota3, quota1 - 1)

    def test_format_restrictions(self):
        """测试格式限制"""
        # 免费版
        self.user.quota_plan = 'free'
        self.user.save()
        
        # 检查允许的格式
        self.assertTrue(self.quota_manager.can_use_format(self.user, 'pdf'))
        self.assertTrue(self.quota_manager.can_use_format(self.user, 'txt'))
        self.assertFalse(self.quota_manager.can_use_format(self.user, 'jpg'))
        
        # 高级版
        self.user.quota_plan = 'premium'
        self.user.save()
        
        # 检查更多格式支持
        self.assertTrue(self.quota_manager.can_use_format(self.user, 'jpg'))
        self.assertTrue(self.quota_manager.can_use_format(self.user, 'png'))

    def test_concurrent_tasks_limit(self):
        """测试并发任务限制"""
        self.user.quota_plan = 'free'
        self.user.save()
        
        # 创建任务
        task1 = ConversionTask.objects.create(
            user=self.user,
            status='processing'
        )
        
        # 检查是否可以创建更多任务
        self.assertFalse(
            self.quota_manager.can_create_task(self.user)
        )
        
        # 升级到基础版
        self.user.quota_plan = 'basic'
        self.user.save()
        
        # 现在可以创建更多任务
        self.assertTrue(
            self.quota_manager.can_create_task(self.user)
        )

    def test_daily_quota_limit(self):
        """测试每日配额限制"""
        # 设置每日限制
        self.user.quota_plan = 'basic'
        self.user.save()
        
        # 创建接近限制的任务
        for _ in range(48):  # basic计划每日限额50
            ConversionTask.objects.create(
                user=self.user,
                status='completed',
                created_at=timezone.now()
            )
        
        # 检查是否还能创建任务
        self.assertTrue(self.quota_manager.can_create_task(self.user))
        
        # 创建超出限制的任务
        for _ in range(3):
            ConversionTask.objects.create(
                user=self.user,
                status='completed',
                created_at=timezone.now()
            )
        
        # 验证已达到限制
        self.assertFalse(self.quota_manager.can_create_task(self.user))

    def test_file_type_restrictions(self):
        """测试文件类型限制"""
        test_cases = [
            ('free', 'pdf', True),
            ('free', 'jpg', False),
            ('basic', 'xlsx', True),
            ('basic', 'png', False),
            ('premium', 'png', True),
            ('premium', 'invalid', False),
        ]
        
        for plan, file_type, expected in test_cases:
            self.user.quota_plan = plan
            self.user.save()
            
            result = self.quota_manager.can_use_format(self.user, file_type)
            self.assertEqual(
                result,
                expected,
                f"Plan {plan} should {'allow' if expected else 'deny'} {file_type}"
            )

    def test_batch_size_limits(self):
        """测试批量处理限制"""
        test_cases = [
            ('free', 1),
            ('basic', 5),
            ('premium', 10)
        ]
        
        for plan, expected_limit in test_cases:
            self.user.quota_plan = plan
            self.user.save()
            
            limit = self.quota_manager.get_batch_size_limit(self.user)
            self.assertEqual(
                limit,
                expected_limit,
                f"Plan {plan} should have batch limit of {expected_limit}"
            )

    def test_priority_queue_features(self):
        """测试优先队列特性"""
        # 创建多个任务
        tasks = []
        for i in range(5):
            task = ConversionTask.objects.create(
                user=self.user,
                status='pending',
                priority=i % 2  # 交替设置优先级
            )
            tasks.append(task)
        
        # 测试普通用户无法使用优先级
        self.user.quota_plan = 'basic'
        self.user.save()
        
        task = ConversionTask.objects.create(
            user=self.user,
            status='pending',
            priority=1
        )
        self.assertEqual(task.priority, 0)  # 应该被重置为普通优先级
        
        # 测试高级用户可以使用优先级
        self.user.quota_plan = 'premium'
        self.user.save()
        
        task = ConversionTask.objects.create(
            user=self.user,
            status='pending',
            priority=1
        )
        self.assertEqual(task.priority, 1)  # 应该保持高优先级

    def test_quota_expiration(self):
        """测试配额过期"""
        # 设置过期时间
        expiry_date = timezone.now() + timezone.timedelta(days=30)
        self.user.quota_plan = 'premium'
        self.user.plan_expiry_date = expiry_date
        self.user.save()
        
        # 检查当前可以使用高级功能
        self.assertTrue(self.quota_manager.can_use_feature(self.user, 'priority_queue'))
        
        # 模拟过期
        self.user.plan_expiry_date = timezone.now() - timezone.timedelta(days=1)
        self.user.save()
        
        # 验证降级到免费版
        self.assertFalse(self.quota_manager.can_use_feature(self.user, 'priority_queue'))
        self.assertEqual(self.quota_manager.get_effective_plan(self.user), 'free')

    def test_usage_tracking(self):
        """测试使用量追踪"""
        start_time = timezone.now()
        
        # 创建一些测试数据
        for i in range(5):
            ConversionTask.objects.create(
                user=self.user,
                status='completed',
                file_size=1024 * (i + 1),
                created_at=start_time + timezone.timedelta(hours=i)
            )
        
        # 获取使用统计
        stats = self.quota_manager.get_usage_stats(self.user)
        
        # 验证统计数据
        self.assertEqual(stats['total_tasks'], 5)
        self.assertEqual(stats['total_size'], sum(1024 * (i + 1) for i in range(5)))
        self.assertEqual(len(stats['hourly_usage']), 5)
        
        # 验证趋势分析
        trends = self.quota_manager.analyze_usage_trends(self.user)
        self.assertIn('usage_trend', trends)
        self.assertIn('peak_hours', trends)

    def test_batch_conversion_permission(self):
        """测试批量转换权限"""
        # 免费版不能批量转换
        self.user.quota_plan = 'free'
        self.user.save()
        
        self.assertFalse(
            self.quota_manager.can_use_batch_conversion(self.user)
        )
        
        # 基础版可以批量转换
        self.user.quota_plan = 'basic'
        self.user.save()
        
        self.assertTrue(
            self.quota_manager.can_use_batch_conversion(self.user)
        )

    def test_priority_queue_access(self):
        """测试优先队列访问"""
        # 只有高级版可以使用优先队列
        self.user.quota_plan = 'basic'
        self.user.save()
        
        self.assertFalse(
            self.quota_manager.can_use_priority_queue(self.user)
        )
        
        self.user.quota_plan = 'premium'
        self.user.save()
        
        self.assertTrue(
            self.quota_manager.can_use_priority_queue(self.user)
        )

    def test_quota_upgrade_effects(self):
        """测试配额升级效果"""
        # 使用部分免费版配额
        self.user.quota_plan = 'free'
        self.user.save()
        
        for _ in range(5):
            self.quota_manager.use_quota(
                self.user,
                1024 * 1024
            )
        
        # 升级到高级版
        self.user.quota_plan = 'premium'
        self.user.save()
        
        # 验证新的配额限制
        remaining = self.quota_manager.get_remaining_quota(self.user)
        self.assertEqual(remaining, 95)  # 100 - 5

    def test_quota_downgrade_handling(self):
        """测试配额降级处理"""
        # 先使用高级版配额
        self.user.quota_plan = 'premium'
        self.user.save()
        
        for _ in range(20):
            self.quota_manager.use_quota(
                self.user,
                1024 * 1024
            )
        
        # 降级到免费版
        self.user.quota_plan = 'free'
        self.user.save()
        
        # 验证配额状态
        self.assertFalse(
            self.quota_manager.can_use_quota(self.user)
        )
        
        # 检查警告消息
        alerts = self.quota_manager.get_quota_alerts(self.user)
        self.assertTrue(any(
            alert['type'] == 'quota_exceeded'
            for alert in alerts
        ))

    def test_feature_access_control(self):
        """测试功能访问控制"""
        features_by_plan = {
            'free': ['basic_conversion'],
            'basic': ['basic_conversion', 'batch_conversion'],
            'premium': ['basic_conversion', 'batch_conversion', 'priority_queue']
        }
        
        for plan, features in features_by_plan.items():
            self.user.quota_plan = plan
            self.user.save()
            
            for feature in features:
                self.assertTrue(
                    self.quota_manager.can_use_feature(self.user, feature),
                    f"Plan {plan} should have access to {feature}"
                )

    def test_usage_statistics(self):
        """测试使用统计"""
        # 创建一些转换记录
        for _ in range(5):
            ConversionTask.objects.create(
                user=self.user,
                status='completed',
                file_size=1024 * 1024,
                created_at=timezone.now()
            )
        
        # 获取统计数据
        stats = self.quota_manager.get_usage_stats(self.user)
        
        # 验证统计结果
        self.assertEqual(stats['total_conversions'], 5)
        self.assertEqual(stats['total_size'], 5 * 1024 * 1024)
        self.assertEqual(stats['successful_conversions'], 5)

    def test_quota_notification_cooldown(self):
        """测试配额通知冷却"""
        # 触发第一次警告
        self.quota_manager._send_quota_alert(
            self.user,
            'warning',
            remaining=2
        )
        
        # 清空邮件队列
        from django.core import mail
        mail.outbox = []
        
        # 立即尝试发送另一个警告
        self.quota_manager._send_quota_alert(
            self.user,
            'warning',
            remaining=1
        )
        
        # 验证没有发送新的通知
        self.assertEqual(len(mail.outbox), 0)

    def test_concurrent_plan_change(self):
        """测试并发计划变更"""
        def change_plan():
            self.user.quota_plan = 'premium'
            self.user.save()
            time.sleep(0.1)
            self.user.quota_plan = 'basic'
            self.user.save()

        def use_features():
            for _ in range(5):
                result = self.quota_manager.can_use_feature(self.user, 'priority_queue')
                time.sleep(0.1)

        # 创建并发线程
        threads = [
            threading.Thread(target=change_plan),
            threading.Thread(target=use_features)
        ]

        # 启动线程
        for t in threads:
            t.start()

        # 等待完成
        for t in threads:
            t.join()

        # 验证最终状态一致性
        self.assertEqual(self.user.quota_plan, 'basic')
        self.assertFalse(self.quota_manager.can_use_feature(self.user, 'priority_queue'))

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的计划类型
        self.user.quota_plan = 'invalid_plan'
        self.user.save()
        
        # 应该降级到免费版
        self.assertEqual(
            self.quota_manager.get_effective_plan(self.user),
            'free'
        )
        
        # 测试无效的配额使用
        with self.assertRaises(ValueError):
            self.quota_manager.use_quota(self.user, -1024)
        
        # 测试无效的特性检查
        self.assertFalse(
            self.quota_manager.can_use_feature(self.user, 'nonexistent_feature')
        )

    def test_quota_recovery(self):
        """测试配额恢复"""
        # 使用所有配额
        self.user.quota_plan = 'basic'
        self.user.save()
        
        for _ in range(50):  # 用完basic版配额
            self.quota_manager.use_quota(self.user, 1024)
        
        # 验证配额已用完
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 0)
        
        # 模拟月底重置
        self.quota_manager.reset_quota(self.user)
        
        # 验证配额已恢复
        self.assertEqual(
            self.quota_manager.get_remaining_quota(self.user),
            settings.QUOTA_SETTINGS['plans']['basic']['conversions']
        )

    def test_plan_inheritance(self):
        """测试计划继承"""
        # 创建组织账户
        org_user = User.objects.create_user(
            username='org',
            email='org@example.com',
            password='testpass123',
            quota_plan='premium'
        )
        self.user.organization = org_user
        self.user.save()
        
        # 验证继承组织的计划特性
        self.assertTrue(
            self.quota_manager.can_use_feature(self.user, 'priority_queue')
        )
        
        # 测试组织降级
        org_user.quota_plan = 'basic'
        org_user.save()
        
        # 验证用户特性也随之降级
        self.assertFalse(
            self.quota_manager.can_use_feature(self.user, 'priority_queue')
        )

    def test_quota_transfer(self):
        """测试配额转移"""
        # 创建另一个用户
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        
        # 使用一些配额
        self.quota_manager.use_quota(self.user, 1024)
        
        # 转移配额到新用户
        with transaction.atomic():
            remaining = self.quota_manager.get_remaining_quota(self.user)
            self.user.used_quota = self.user.quota_plan_limit
            other_user.used_quota = 0
            self.user.save()
            other_user.save()
        
        # 验证转移结果
        self.assertEqual(self.quota_manager.get_remaining_quota(self.user), 0)
        self.assertEqual(
            self.quota_manager.get_remaining_quota(other_user),
            settings.QUOTA_SETTINGS['plans']['free']['conversions']
        )

    def test_quota_suspension(self):
        """测试配额暂停"""
        # 暂停用户配额
        self.user.is_active = False
        self.user.save()
        
        # 验证无法使用任何功能
        self.assertFalse(self.quota_manager.can_use_quota(self.user))
        self.assertFalse(self.quota_manager.can_create_task(self.user))
        
        # 恢复用户
        self.user.is_active = True
        self.user.save()
        
        # 验证功能恢复
        self.assertTrue(self.quota_manager.can_use_quota(self.user))

    def test_quota_overflow_protection(self):
        """测试配额溢出保护"""
        # 尝试设置超大配额使用量
        max_int = 2**31 - 1
        
        with self.assertRaises(ValueError):
            self.quota_manager.use_quota(self.user, max_int)
        
        # 验证配额未变化
        self.assertEqual(self.user.used_quota, 0)

    def test_plan_feature_combinations(self):
        """测试计划特性组合"""
        feature_combinations = {
            'free': {
                'can_download': True,
                'can_batch_convert': False,
                'can_use_priority': False,
                'max_file_size': 10 * 1024 * 1024
            },
            'basic': {
                'can_download': True,
                'can_batch_convert': True,
                'can_use_priority': False,
                'max_file_size': 50 * 1024 * 1024
            },
            'premium': {
                'can_download': True,
                'can_batch_convert': True,
                'can_use_priority': True,
                'max_file_size': 100 * 1024 * 1024
            }
        }
        
        for plan, features in feature_combinations.items():
            self.user.quota_plan = plan
            self.user.save()
            
            for feature, expected in features.items():
                actual = self.quota_manager.check_feature_access(self.user, feature)
                self.assertEqual(
                    actual,
                    expected,
                    f"Plan {plan} should have {feature} = {expected}"
                )

    def tearDown(self):
        cache.clear() 