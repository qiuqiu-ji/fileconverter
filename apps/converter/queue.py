"""任务队列实现"""
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from apps.core.exceptions import *
import heapq
import json

class TaskQueue:
    """任务队列"""
    MAX_SIZE = 1000  # 最大队列容量
    MAX_USER_TASKS = 10  # 每个用户最大任务数
    CACHE_KEY = 'task_queue_state'

    PRIORITY_WEIGHTS = {
        'high': 0,
        'medium': 50,
        'low': 100
    }

    def __init__(self):
        self._queue = []
        self._task_set = set()
        self.restore_state()

    def push(self, task):
        """添加任务到队列"""
        if len(self._queue) >= self.MAX_SIZE:
            raise QueueFullError("Queue capacity exceeded")

        # 检查用户任务数限制
        user_tasks = len([t for t in self._queue if t.user_id == task.user_id])
        if user_tasks >= self.MAX_USER_TASKS:
            raise UserTaskLimitError("User task limit exceeded")

        # 计算优先级分数
        score = self._calculate_priority(task)

        # 添加到队列
        heapq.heappush(self._queue, (score, task.id, task))
        self._task_set.add(task.id)
        self._save_state()

    def pop(self):
        """获取下一个要处理的任务"""
        while self._queue:
            score, task_id, task = heapq.heappop(self._queue)
            self._task_set.remove(task_id)

            # 检查任务是否仍然有效
            task.refresh_from_db()
            if task.status != 'pending':
                continue

            # 检查依赖任务
            if task.parent_task and task.parent_task.status != 'completed':
                raise TaskDependencyError("Parent task not completed")

            return task

        return None

    def _calculate_priority(self, task):
        """计算任务优先级分数"""
        base_score = self.PRIORITY_WEIGHTS.get(task.priority, 50)
        wait_time = (timezone.now() - task.created_at).total_seconds()
        
        # 等待时间越长，优先级越高
        time_factor = max(0, wait_time / 3600)  # 每小时增加优先级
        
        return base_score - time_factor

    def is_empty(self):
        """检查队列是否为空"""
        return len(self._queue) == 0

    def cleanup_timeouts(self):
        """清理超时任务"""
        from .state_machine import TaskStateMachine

        new_queue = []
        for score, task_id, task in self._queue:
            state_machine = TaskStateMachine(task)
            if state_machine.is_timed_out():
                state_machine.handle_timeout()
                self._task_set.remove(task_id)
            else:
                new_queue.append((score, task_id, task))

        self._queue = new_queue
        heapq.heapify(self._queue)
        self._save_state()

    def _save_state(self):
        """保存队列状态"""
        state = {
            'tasks': [(s, tid) for s, tid, _ in self._queue],
            'task_set': list(self._task_set)
        }
        cache.set(self.CACHE_KEY, json.dumps(state), timeout=None)

    def restore_state(self):
        """恢复队列状态"""
        from apps.converter.models import ConversionTask
        
        state_data = cache.get(self.CACHE_KEY)
        if not state_data:
            return

        state = json.loads(state_data)
        self._task_set = set(state['task_set'])
        
        # 重建队列
        tasks = ConversionTask.objects.filter(id__in=self._task_set)
        task_map = {str(t.id): t for t in tasks}
        
        self._queue = [
            (score, tid, task_map[tid])
            for score, tid in state['tasks']
            if tid in task_map
        ]
        heapq.heapify(self._queue)
 