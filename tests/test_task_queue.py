"""任务队列测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.converter.models import ConversionTask
from apps.converter.queue import TaskQueue
from apps.core.exceptions import *
import time

User = get_user_model()

class TaskQueueTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.queue = TaskQueue()

    def test_task_priority(self):
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
            self.queue.push(task)

        # 验证任务按优先级顺序处理
        processed = []
        while not self.queue.is_empty():
            task = self.queue.pop()
            processed.append(task.priority)

        self.assertEqual(processed, ['high', 'medium', 'low'])

    def test_queue_capacity(self):
        """测试队列容量限制"""
        # 创建超过容量的任务
        for i in range(TaskQueue.MAX_SIZE + 1):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )
            if i < TaskQueue.MAX_SIZE:
                self.queue.push(task)
            else:
                with self.assertRaises(QueueFullError):
                    self.queue.push(task)

    def test_task_timeout(self):
        """测试任务超时处理"""
        # 创建一个任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )
        self.queue.push(task)

        # 模拟任务超时
        task.started_at = timezone.now() - timezone.timedelta(hours=2)
        task.save()

        # 验证超时任务被移除
        self.queue.cleanup_timeouts()
        self.assertTrue(self.queue.is_empty())
        
        # 验证任务状态
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIn('timeout', task.error_message.lower())

    def test_user_task_limit(self):
        """测试用户任务数限制"""
        # 创建超过限制的任务
        for i in range(TaskQueue.MAX_USER_TASKS + 1):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )
            if i < TaskQueue.MAX_USER_TASKS:
                self.queue.push(task)
            else:
                with self.assertRaises(UserTaskLimitError):
                    self.queue.push(task)

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
        self.queue.push(parent_task)

        # 创建依赖任务
        child_task = ConversionTask.objects.create(
            user=self.user,
            original_file='child.txt',
            original_format='txt',
            target_format='pdf',
            status='pending',
            parent_task=parent_task
        )
        self.queue.push(child_task)

        # 验证处理顺序
        first_task = self.queue.pop()
        self.assertEqual(first_task.id, parent_task.id)

        # 父任务未完成时不能处理子任务
        with self.assertRaises(TaskDependencyError):
            self.queue.pop()

        # 完成父任务后可以处理子任务
        parent_task.status = 'completed'
        parent_task.save()
        next_task = self.queue.pop()
        self.assertEqual(next_task.id, child_task.id)

    def test_queue_persistence(self):
        """测试队列持久化"""
        # 创建任务并加入队列
        tasks = []
        for i in range(3):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf',
                status='pending'
            )
            tasks.append(task)
            self.queue.push(task)

        # 模拟服务重启
        new_queue = TaskQueue()
        new_queue.restore_state()

        # 验证队列状态恢复
        for task in tasks:
            queued_task = new_queue.pop()
            self.assertEqual(queued_task.id, task.id) 