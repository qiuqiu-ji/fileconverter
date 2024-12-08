"""WebSocket通信测试"""
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.converter.routing import application
from apps.converter.models import ConversionTask
import json
import asyncio

User = get_user_model()

class WebSocketTest(TestCase):
    async def setUp(self):
        self.user = await self.create_user()
        self.task = await self.create_task()

    @staticmethod
    async def create_user():
        return await asyncio.get_event_loop().run_in_executor(
            None,
            User.objects.create_user,
            'test@example.com',
            'testuser',
            'testpass123'
        )

    async def create_task(self):
        return await asyncio.get_event_loop().run_in_executor(
            None,
            ConversionTask.objects.create,
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

    async def test_connect(self):
        """测试WebSocket连接"""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{self.task.id}/"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_task_updates(self):
        """测试任务状态更新"""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{self.task.id}/"
        )
        await communicator.connect()

        # 模拟任务状态更新
        self.task.status = 'processing'
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.task.save
        )

        # 接收更新消息
        response = await communicator.receive_json_from()
        self.assertEqual(response['status'], 'processing')
        self.assertEqual(response['task_id'], str(self.task.id))

        await communicator.disconnect()

    async def test_progress_updates(self):
        """测试进度更新"""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{self.task.id}/"
        )
        await communicator.connect()

        # 模拟进度更新
        progress_data = {
            'task_id': str(self.task.id),
            'progress': 50,
            'status': 'processing'
        }
        await communicator.send_json_to(progress_data)

        # 接收确认消息
        response = await communicator.receive_json_from()
        self.assertEqual(response['progress'], 50)

        await communicator.disconnect()

    async def test_error_handling(self):
        """测试错误处理"""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/invalid-id/"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        # 测试无效消息
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{self.task.id}/"
        )
        await communicator.connect()
        
        await communicator.send_json_to({'invalid': 'data'})
        response = await communicator.receive_json_from()
        self.assertEqual(response['error'], 'Invalid message format')

        await communicator.disconnect()

    async def test_multiple_clients(self):
        """测试多客户端连接"""
        # 创建多个客户端连接
        communicators = []
        for _ in range(3):
            communicator = WebsocketCommunicator(
                application,
                f"/ws/conversion/{self.task.id}/"
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            communicators.append(communicator)

        # 模拟状态更新
        self.task.status = 'completed'
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.task.save
        )

        # 验证所有客户端都收到更新
        for communicator in communicators:
            response = await communicator.receive_json_from()
            self.assertEqual(response['status'], 'completed')

        # 断开所有连接
        for communicator in communicators:
            await communicator.disconnect()

    async def test_authentication(self):
        """测试WebSocket认证"""
        # 未认证用户
        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{self.task.id}/"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

        # 其他用户的任务
        other_user = await self.create_user()
        other_task = await asyncio.get_event_loop().run_in_executor(
            None,
            ConversionTask.objects.create,
            user=other_user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        communicator = WebsocketCommunicator(
            application,
            f"/ws/conversion/{other_task.id}/"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected) 