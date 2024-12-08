"""缓存测试"""
from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask
from apps.converter.cache import TaskCache
import time

User = get_user_model()

class CacheTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
        cache.clear()

    def test_task_caching(self):
        """测试任务缓存"""
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        # 首次获取任务（从数据库）
        start_time = time.time()
        response1 = self.client.get(reverse('converter:task_status', args=[task.id]))
        db_time = time.time() - start_time

        # 再次获取任��（从缓存）
        start_time = time.time()
        response2 = self.client.get(reverse('converter:task_status', args=[task.id]))
        cache_time = time.time() - start_time

        # 验证缓存是否生效
        self.assertLess(cache_time, db_time)
        self.assertEqual(response1.content, response2.content)

    def test_cache_invalidation(self):
        """测试缓存失效"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        # 获取初始状态
        response1 = self.client.get(reverse('converter:task_status', args=[task.id]))
        initial_data = response1.json()

        # 更新任务状态
        task.status = 'completed'
        task.save()

        # 再次获取状态
        response2 = self.client.get(reverse('converter:task_status', args=[task.id]))
        updated_data = response2.json()

        # 验证是否获取到更新后的状态
        self.assertNotEqual(initial_data['status'], updated_data['status'])

    def test_cache_cleanup(self):
        """测试缓存清理"""
        # 创建多个任务
        tasks = []
        for i in range(5):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf'
            )
            tasks.append(task)
            TaskCache.set_task(task)

        # 删除部分任务
        tasks[0].delete()
        tasks[1].delete()

        # 验证缓存是否被清理
        self.assertIsNone(TaskCache.get_task(tasks[0].id))
        self.assertIsNone(TaskCache.get_task(tasks[1].id))
        self.assertIsNotNone(TaskCache.get_task(tasks[2].id))

    def test_cache_expiration(self):
        """测试缓存过期"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        # 设置短期缓存
        TaskCache.set_task(task, timeout=1)

        # 验证缓存存在
        self.assertIsNotNone(TaskCache.get_task(task.id))

        # 等待缓存过期
        time.sleep(2)

        # 验证缓存已过期
        self.assertIsNone(TaskCache.get_task(task.id))

    def test_cache_race_condition(self):
        """测试缓存竞态条件"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        def update_task():
            # 模拟并发更新
            t = ConversionTask.objects.get(id=task.id)
            t.status = 'processing'
            time.sleep(0.1)  # 模拟处理延迟
            t.save()

        # 创建多个线程同时更新
        import threading
        threads = [
            threading.Thread(target=update_task)
            for _ in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证缓存和数据库一致性
        cached_task = TaskCache.get_task(task.id)
        db_task = ConversionTask.objects.get(id=task.id)
        self.assertEqual(cached_task.status, db_task.status) 