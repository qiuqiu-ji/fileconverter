"""任务调度器"""
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import ConversionTask
from .queue import TaskQueue
from .state_machine import TaskStateMachine
import threading
import logging
import psutil
import time

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器"""
    MAX_CONCURRENT_TASKS = getattr(settings, 'MAX_CONCURRENT_TASKS', 5)
    CHECK_INTERVAL = 1  # 检查间隔（秒）

    def __init__(self):
        self.queue = TaskQueue()
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

    def start(self):
        """启动调度器"""
        with self._lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Task scheduler started")

    def stop(self):
        """停止调度器"""
        with self._lock:
            if not self.running:
                return
            self.running = False
            if self.thread:
                self.thread.join()
            logger.info("Task scheduler stopped")

    def _run(self):
        """调度器主循环"""
        while self.running:
            try:
                self._check_resources()
                self._recover_tasks()
                self._process_tasks()
            except Exception as e:
                logger.exception("Error in scheduler loop: %s", str(e))
            time.sleep(self.CHECK_INTERVAL)

    def _check_resources(self):
        """检查系统资源"""
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()

        if cpu_usage > 90 or memory_usage > 90:
            logger.warning(
                "System resources critical: CPU=%d%%, Memory=%d%%",
                cpu_usage, memory_usage
            )
            time.sleep(5)  # 等待资源释放
            return False
        return True

    def _recover_tasks(self):
        """恢复中断的任务"""
        # 查找所有处理中但已超时的任务
        stuck_tasks = ConversionTask.objects.filter(
            status='processing',
            started_at__lt=timezone.now() - timezone.timedelta(hours=1)
        )

        for task in stuck_tasks:
            try:
                state_machine = TaskStateMachine(task)
                if state_machine.is_timed_out():
                    state_machine.handle_timeout()
                    logger.warning("Recovered stuck task: %s", task.id)
            except Exception as e:
                logger.error("Error recovering task %s: %s", task.id, str(e))

    def _process_tasks(self):
        """处理任务"""
        # 检查当前处理中的任务数
        processing_count = ConversionTask.objects.filter(
            status='processing'
        ).count()

        if processing_count >= self.MAX_CONCURRENT_TASKS:
            return

        # 获取可处理的任务数
        available_slots = self.MAX_CONCURRENT_TASKS - processing_count

        # 处理任务
        for _ in range(available_slots):
            if not self._check_resources():
                break

            try:
                task = self.queue.pop()
                if not task:
                    break

                self._process_task(task)

            except Exception as e:
                logger.exception("Error processing task: %s", str(e))

    @transaction.atomic
    def _process_task(self, task):
        """处理单个任务"""
        try:
            # 更新任务状态
            state_machine = TaskStateMachine(task)
            state_machine.transition_to('processing')

            # 启动转换进程
            from .tasks import convert_file_task
            convert_file_task.delay(task.id)

            logger.info("Started processing task: %s", task.id)

        except Exception as e:
            logger.error("Error starting task %s: %s", task.id, str(e))
            task.error_message = str(e)
            task.status = 'failed'
            task.save()

    @staticmethod
    def get_cpu_usage():
        """获取CPU使用率"""
        return psutil.cpu_percent()

    @staticmethod
    def get_memory_usage():
        """获取内存使用率"""
        return psutil.virtual_memory().percent

    @property
    def is_running(self):
        """检查调度器是否运行中"""
        return self.running 