"""任务错误处理测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.core.exceptions import *
from apps.converter.models import ConversionTask
import json
import threading
import time

User = get_user_model()

class TaskErrorHandlingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_task_state_error(self):
        """测试任务状态错误"""
        # 创建已完成的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='completed'
        )
        
        # 尝试重新开始任务
        response = self.client.post(reverse('converter:start_task'), {
            'task_id': task.id
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('invalid state', data['error'].lower())

    def test_task_not_found(self):
        """测试任务不存在错误"""
        response = self.client.get(reverse('converter:task_status', args=['nonexistent-id']))
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('not found', data['error'].lower())

    def test_invalid_operation(self):
        """测试无效操作错误"""
        # 创建进行中的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='processing'
        )
        
        # 尝试删除进行中的任务
        response = self.client.delete(reverse('converter:delete_task', args=[task.id]))
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('cannot delete', data['error'].lower())

    def test_concurrent_access(self):
        """测试并发访问错误"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )

        def update_task():
            """更新任务状态"""
            response = self.client.post(reverse('converter:update_task'), {
                'task_id': task.id,
                'status': 'processing'
            })
            return response.status_code

        # 创建多个线程同时更新
        threads = [
            threading.Thread(target=update_task)
            for _ in range(5)
        ]

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        responses = []
        for t in threads:
            t.join()

        # 验证只有一个请求成功，其他都失败
        task.refresh_from_db()
        self.assertEqual(task.status, 'processing')

    def test_deadlock_prevention(self):
        """测试死锁预防"""
        task1 = ConversionTask.objects.create(
            user=self.user,
            original_file='test1.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )
        
        task2 = ConversionTask.objects.create(
            user=self.user,
            original_file='test2.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )

        def update_tasks(task_a, task_b):
            """更新两个任务"""
            self.client.post(reverse('converter:update_task'), {
                'task_id': task_a,
                'status': 'processing'
            })
            time.sleep(0.1)  # 模拟处理时间
            self.client.post(reverse('converter:update_task'), {
                'task_id': task_b,
                'status': 'processing'
            })

        # 创建两个线程，以不同顺序更新任务
        t1 = threading.Thread(target=update_tasks, args=(task1.id, task2.id))
        t2 = threading.Thread(target=update_tasks, args=(task2.id, task1.id))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 验证没有死锁发生
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertIn(task1.status, ['pending', 'processing'])
        self.assertIn(task2.status, ['pending', 'processing'])

    def test_error_logging(self):
        """测试错误日志记录"""
        with self.assertLogs('apps.core', level='ERROR') as logs:
            # 触发一系列错误
            self.client.post(reverse('converter:start_task'), {
                'task_id': 'invalid-id'
            })
            self.client.post(reverse('converter:update_task'), {
                'task_id': 'invalid-id'
            })
            
            # 验证错误被正确记录
            self.assertTrue(any('Task not found' in log for log in logs.output))
            self.assertTrue(any('Error updating task' in log for log in logs.output)) 