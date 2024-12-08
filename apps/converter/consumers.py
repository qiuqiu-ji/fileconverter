import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ConversionTask
from django.utils.translation import gettext as _

class ConversionProgressConsumer(AsyncWebsocketConsumer):
    """转换进度WebSocket消费者"""

    async def connect(self):
        """建立连接"""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'conversion_{self.task_id}'

        # 验证用户权限
        if not await self.can_access_task():
            await self.close()
            return

        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """断开连接"""
        # 离开房间组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """接收消息"""
        pass  # 客户端不需要发送消息

    async def conversion_progress(self, event):
        """发送转换进度"""
        await self.send(text_data=json.dumps({
            'type': 'conversion_progress',
            'progress': event['progress'],
            'status': event['status'],
            'message': event.get('message')
        }))

    @database_sync_to_async
    def can_access_task(self):
        """检查用户是否有权限访问任务"""
        try:
            task = ConversionTask.objects.get(id=self.task_id)
            return task.user_id == self.scope['user'].id
        except ConversionTask.DoesNotExist:
            return False

class BatchProgressConsumer(AsyncWebsocketConsumer):
    """批量转换进度WebSocket消费者"""

    async def connect(self):
        """建立连接"""
        self.batch_id = self.scope['url_route']['kwargs']['batch_id']
        self.room_group_name = f'batch_{self.batch_id}'

        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """断开连接"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """接收消息"""
        pass

    async def batch_progress(self, event):
        """发送批量转换进度"""
        await self.send(text_data=json.dumps({
            'type': 'batch_progress',
            'total': event['total'],
            'completed': event['completed'],
            'failed': event['failed'],
            'progress': event['progress'],
            'status': event['status'],
            'message': event.get('message')
        })) 

class ConversionConsumer(AsyncWebsocketConsumer):
    """转换进度消费者(添加心跳和重连)"""
    
    async def connect(self):
        """建立连接"""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.group_name = f'task_{self.task_id}'
        self.reconnect_attempts = 0
        self.max_reconnects = 3
        
        try:
            # 加入任务组
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # 启动心跳
            self.heartbeat_task = asyncio.create_task(self.heartbeat())
            
            await self.accept()
            
            # 发送初始状态
            task = await self.get_task()
            if task:
                await self.send_status(task)
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """断开连接"""
        # 取消心跳
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
            
        # 离开任务组
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def heartbeat(self):
        """心跳检测"""
        while True:
            try:
                await self.send(json.dumps({'type': 'ping'}))
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                if self.reconnect_attempts < self.max_reconnects:
                    self.reconnect_attempts += 1
                    await asyncio.sleep(1)
                    continue
                break
    
    async def receive(self, text_data):
        """接收消息"""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'pong':
                self.reconnect_attempts = 0
        except json.JSONDecodeError:
            pass 