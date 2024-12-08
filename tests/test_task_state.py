"""任务状态转换测试"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.core.exceptions import TaskStateError
from apps.converter.models import ConversionTask
from apps.converter.state_machine import TaskStateMachine

User = get_user_model()

class TaskStateTransitionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='pending'
        )
        self.state_machine = TaskStateMachine(self.task)

    def test_valid_transitions(self):
        """测试有效的状态转换"""
        # pending -> processing
        self.state_machine.transition_to('processing')
        self.assertEqual(self.task.status, 'processing')

        # processing -> completed
        self.state_machine.transition_to('completed')
        self.assertEqual(self.task.status, 'completed')

    def test_invalid_transitions(self):
        """测试无效的状态转换"""
        # pending -> completed (不允许跳过processing)
        with self.assertRaises(TaskStateError):
            self.state_machine.transition_to('completed')

        # 完成后不能重新处理
        self.task.status = 'completed'
        self.task.save()
        with self.assertRaises(TaskStateError):
            self.state_machine.transition_to('processing')

    def test_failed_state_handling(self):
        """测试失败状态处理"""
        # 任务可以从任何状态转为失败
        valid_states = ['pending', 'processing', 'completed']
        for state in valid_states:
            task = ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status=state
            )
            state_machine = TaskStateMachine(task)
            state_machine.transition_to('failed')
            self.assertEqual(task.status, 'failed')

    def test_retry_handling(self):
        """测试重试处理"""
        # 设置任务为失败状态
        self.task.status = 'failed'
        self.task.save()

        # 允许重试
        self.state_machine.retry()
        self.assertEqual(self.task.status, 'pending')
        self.assertEqual(self.task.retry_count, 1)

        # 超过最大重试次数
        self.task.retry_count = 3
        self.task.save()
        with self.assertRaises(TaskStateError):
            self.state_machine.retry()

    def test_cancellation(self):
        """测试取消操作"""
        # 可以取消pending状态的任务
        self.state_machine.cancel()
        self.assertEqual(self.task.status, 'cancelled')

        # 不能取消已完成的任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            status='completed'
        )
        state_machine = TaskStateMachine(task)
        with self.assertRaises(TaskStateError):
            state_machine.cancel()

    def test_state_timeout(self):
        """测试状态超时"""
        import time
        from django.utils import timezone
        
        # 设置任务为处理中状态
        self.task.status = 'processing'
        self.task.started_at = timezone.now() - timezone.timedelta(hours=2)
        self.task.save()

        # 检查是否超时
        self.assertTrue(self.state_machine.is_timed_out())
        
        # 验证超时处理
        self.state_machine.handle_timeout()
        self.assertEqual(self.task.status, 'failed')
        self.assertIn('timeout', self.task.error_message.lower())

    def test_concurrent_state_change(self):
        """测试并发状态变更"""
        import threading
        
        def change_state():
            try:
                state_machine = TaskStateMachine(self.task)
                state_machine.transition_to('processing')
            except TaskStateError:
                pass

        # 创建多个线程同时改变状态
        threads = [threading.Thread(target=change_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证状态只被改变一次
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'processing') 