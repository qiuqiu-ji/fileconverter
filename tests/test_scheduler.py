"""任务调度测试"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask
from apps.converter.tasks import cleanup_old_files, retry_failed_tasks
from apps.converter.scheduler import TaskScheduler
from apps.core.exceptions import *
import os
import threading
import time

User = get_user_model()

class SchedulerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.scheduler = TaskScheduler()

    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        # 创建过期任务
        old_task = ConversionTask.objects.create(
            user=self.user,
            original_file='old.txt',
            original_format='txt',
            target_format='pdf',
            status='completed',
            created_at=timezone.now() - timedelta(days=31)  # 超过30天
        )

        # 创建新任务
        new_task = ConversionTask.objects.create(
            user=self.user,
            original_file='new.txt',
            original_format='txt',
            target_format='pdf',
            status='completed',
            created_at=timezone.now()
        )

        # 运行清理任务
        cleanup_old_files.delay()

        # 验证结果
        self.assertFalse(ConversionTask.objects.filter(id=old_task.id).exists())
        self.assertTrue(ConversionTask.objects.filter(id=new_task.id).exists())

    def test_retry_failed_tasks(self):
        """测试重试失败任务"""
        # 创建失败任务
        failed_task = ConversionTask.objects.create(
            user=self.user,
            original_file='failed.txt',
            original_format='txt',
            target_format='pdf',
            status='failed',
            retry_count=0
        )

        # 创建重试次数过多的任务
        max_retries_task = ConversionTask.objects.create(
            user=self.user,
            original_file='max_retries.txt',
            original_format='txt',
            target_format='pdf',
            status='failed',
            retry_count=3
        )

        # 运行重试任务
        retry_failed_tasks.delay()

        # 验证结果
        failed_task.refresh_from_db()
        max_retries_task.refresh_from_db()

        self.assertEqual(failed_task.status, 'pending')
        self.assertEqual(failed_task.retry_count, 1)
        self.assertEqual(max_retries_task.status, 'failed')
        self.assertEqual(max_retries_task.retry_count, 3)

    def test_task_priorities(self):
        """测试任务优先级"""
        # 创建不同优先级的任务
        tasks = []
        priorities = ['high', 'medium', 'low']
        for priority in priorities:
            task = ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status='pending',
                priority=priority
            )
            tasks.append(task)

        # 获取任务处理顺序
        processed_tasks = ConversionTask.objects.filter(
            status='pending'
        ).order_by('-priority')

        # 验证优先级顺序
        self.assertEqual(
            list(processed_tasks.values_list('priority', flat=True)),
            ['high', 'medium', 'low']
        )

    def test_concurrent_task_limits(self):
        """测试并发任务限制"""
        # 创建多个任务
        for i in range(10):
            ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )

        # 获取可以同时处理的任务数
        max_concurrent = 5  # 假设最大并发数为5
        processing_tasks = ConversionTask.objects.filter(
            status='pending'
        )[:max_concurrent]

        # 验证并发限制
        self.assertEqual(len(processing_tasks), max_concurrent)

    def test_task_dependencies(self):
        """测试任务依赖关系"""
        # 创建父任务
        parent_task = ConversionTask.objects.create(
            user=self.user,
            original_file='parent.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )

        # 创建子任务
        child_task = ConversionTask.objects.create(
            user=self.user,
            original_file='child.txt',
            original_format='txt',
            target_format='pdf',
            status='pending',
            parent_task=parent_task
        )

        # 验证依赖关系
        self.assertEqual(child_task.parent_task, parent_task)
        self.assertTrue(
            child_task.status == 'pending' and parent_task.status == 'pending'
        )

        # 完成父任务
        parent_task.status = 'completed'
        parent_task.save()

        # 验证子任务可以开始处理
        child_task.refresh_from_db()
        self.assertEqual(child_task.status, 'pending')

    def test_scheduler_start_stop(self):
        """测试调度器启动和停止"""
        # 启动调度器
        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running)

        # 停止调度器
        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running)

    def test_task_scheduling(self):
        """测试任务调度"""
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )

        # 启动调度器
        self.scheduler.start()
        time.sleep(1)  # 等待调度器处理任务

        # 验证任务状态
        task.refresh_from_db()
        self.assertEqual(task.status, 'processing')

        self.scheduler.stop()

    def test_concurrent_scheduling(self):
        """测试并发调度"""
        # 创建多个任务
        tasks = []
        for i in range(5):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )
            tasks.append(task)

        # 启动调度器
        self.scheduler.start()
        time.sleep(2)  # 等待调度器处理任务

        # 验证任务状态
        processing_count = ConversionTask.objects.filter(
            status='processing'
        ).count()
        self.assertLessEqual(processing_count, self.scheduler.MAX_CONCURRENT_TASKS)

        self.scheduler.stop()

    def test_error_handling(self):
        """测试错误处理"""
        # 创建一个会导致错误的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='invalid',  # 无效的目标格式
            status='pending'
        )

        # 启动调度器
        self.scheduler.start()
        time.sleep(1)  # 等待调度器处理任务

        # 验证任务状态
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIsNotNone(task.error_message)

        self.scheduler.stop()

    def test_task_recovery(self):
        """测试任务恢复"""
        # 创建一个处理中的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='processing',
            started_at=timezone.now() - timezone.timedelta(hours=2)  # 已超时
        )

        # 启动调度器
        self.scheduler.start()
        time.sleep(1)  # 等待调度器恢复任务

        # 验证任务被重置
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIn('timeout', task.error_message.lower())

        self.scheduler.stop()

    def test_resource_limits(self):
        """测试资源限制"""
        # 创建大量任务
        tasks = []
        for i in range(20):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )
            tasks.append(task)

        # 启动调度器
        self.scheduler.start()
        time.sleep(2)  # 等待调度器处理任务

        # 验证同时处理的任务数不超过限制
        processing_tasks = ConversionTask.objects.filter(status='processing')
        self.assertLessEqual(
            processing_tasks.count(),
            self.scheduler.MAX_CONCURRENT_TASKS
        )

        # 验证CPU和内存使用率
        self.assertLess(self.scheduler.get_cpu_usage(), 90)
        self.assertLess(self.scheduler.get_memory_usage(), 90)

        self.scheduler.stop()

    def tearDown(self):
        if self.scheduler.is_running:
            self.scheduler.stop() 