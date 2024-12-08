"""安全监控可靠性测试"""
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.cache import cache
from django.test.utils import override_settings
from apps.security.monitoring import SecurityMonitor
from apps.security.models import SecurityLog, SecurityAlert
from datetime import timedelta
import threading
import random

class SecurityReliabilityTest(TransactionTestCase):
    """安全可靠性测试"""
    
    def setUp(self):
        self.monitor = SecurityMonitor()
        
    def test_data_consistency(self):
        """测试数据一致性"""
        # 模拟并发写入
        def create_logs():
            for _ in range(100):
                SecurityLog.objects.create(
                    type='attack',
                    attack_type='sql_injection',
                    source_ip='192.168.1.1',
                    timestamp=timezone.now()
                )
                
        threads = [
            threading.Thread(target=create_logs)
            for _ in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # 验证数据完整性
        total_logs = SecurityLog.objects.count()
        self.assertEqual(total_logs, 500)  # 5个线程 * 100条日志
        
    def test_cache_fallback(self):
        """测试缓存故障回退"""
        # 禁用缓存
        with override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}):
            # 创建测试数据
            SecurityLog.objects.create(
                type='attack',
                attack_type='sql_injection',
                source_ip='192.168.1.1'
            )
            
            # 验证监控仍然工作
            stats = self.monitor.monitor_attacks()
            self.assertEqual(stats['sql_injection'], 1)
            
    def test_partial_failure_handling(self):
        """测试部分失败处理"""
        # 模拟部分操作失败
        def failing_operation():
            if random.random() < 0.5:
                raise Exception("Random failure")
            return True
            
        success_count = 0
        total_attempts = 100
        
        for _ in range(total_attempts):
            try:
                if failing_operation():
                    success_count += 1
                SecurityLog.objects.create(
                    type='attack',
                    attack_type='sql_injection',
                    source_ip='192.168.1.1'
                )
            except Exception:
                continue
                
        # 验证部分成功
        self.assertGreater(success_count, 0)
        self.assertLess(success_count, total_attempts)
        
    def test_recovery_after_failure(self):
        """测试故障恢复"""
        # 创建初始数据
        initial_logs = [
            SecurityLog.objects.create(
                type='attack',
                attack_type='sql_injection',
                source_ip='192.168.1.1'
            )
            for _ in range(10)
        ]
        
        # 模拟故障
        with self.assertRaises(Exception):
            with transaction.atomic():
                # 创建新数据
                SecurityLog.objects.create(
                    type='attack',
                    attack_type='sql_injection',
                    source_ip='192.168.1.1'
                )
                raise Exception("Simulated failure")
                
        # 验证数据完整性
        self.assertEqual(
            SecurityLog.objects.count(),
            len(initial_logs)
        )
        
    def test_monitoring_degradation(self):
        """测试监控降级"""
        # 创建大量数据模拟高负载
        SecurityLog.objects.bulk_create([
            SecurityLog(
                type='attack',
                attack_type='sql_injection',
                source_ip=f'192.168.1.{i % 256}',
                timestamp=timezone.now()
            )
            for i in range(10000)
        ])
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行监控
        stats = self.monitor.monitor_attacks()
        
        # 验证降级行为
        self.assertLessEqual(
            time.time() - start_time,
            5.0  # 即使在高负载下也应该在5秒内完成
        )
        
    def tearDown(self):
        cache.clear() 