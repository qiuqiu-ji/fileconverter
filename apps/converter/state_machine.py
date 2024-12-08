"""任务状态机"""
from django.utils import timezone
from django.db import transaction
from apps.core.exceptions import TaskStateError
from django.utils.translation import gettext as _

class TaskStateMachine:
    """任务状态机"""
    # 有效的状态转换
    VALID_TRANSITIONS = {
        'pending': ['processing', 'cancelled', 'failed'],
        'processing': ['completed', 'failed'],
        'completed': ['failed'],
        'failed': ['pending'],  # 通过重试
        'cancelled': []
    }

    # 状态超时时间（小时）
    STATE_TIMEOUTS = {
        'processing': 1,
        'pending': 24
    }

    def __init__(self, task):
        self.task = task

    @transaction.atomic
    def transition_to(self, new_state):
        """转换到新状态"""
        current_state = self.task.status
        
        # 检查转换是否有效
        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            raise TaskStateError(
                _('Invalid state transition from %(current)s to %(new)s') % {
                    'current': current_state,
                    'new': new_state
                }
            )

        # 更新状态
        self.task.status = new_state
        
        # 记录时间戳
        if new_state == 'processing':
            self.task.started_at = timezone.now()
        elif new_state in ['completed', 'failed', 'cancelled']:
            self.task.completed_at = timezone.now()
            if self.task.started_at:
                self.task.processing_time = self.task.completed_at - self.task.started_at

        self.task.save()

    def retry(self):
        """重试失败的任务"""
        if self.task.status != 'failed':
            raise TaskStateError(_('Only failed tasks can be retried'))

        if self.task.retry_count >= 3:  # 最大重试次数
            raise TaskStateError(_('Maximum retry attempts exceeded'))

        self.task.retry_count += 1
        self.transition_to('pending')

    def cancel(self):
        """取消任务"""
        if self.task.status not in ['pending', 'processing']:
            raise TaskStateError(_('Cannot cancel task in %(state)s state') % {
                'state': self.task.status
            })

        self.transition_to('cancelled')

    def is_timed_out(self):
        """检查是否超时"""
        if self.task.status not in self.STATE_TIMEOUTS:
            return False

        timeout_hours = self.STATE_TIMEOUTS[self.task.status]
        if self.task.status == 'processing' and self.task.started_at:
            reference_time = self.task.started_at
        else:
            reference_time = self.task.created_at

        return (timezone.now() - reference_time).total_seconds() > timeout_hours * 3600

    def handle_timeout(self):
        """处理超时"""
        if not self.is_timed_out():
            return

        self.task.error_message = _('Task timed out in %(state)s state') % {
            'state': self.task.status
        }
        self.transition_to('failed') 