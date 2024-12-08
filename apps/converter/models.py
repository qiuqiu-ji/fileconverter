from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import uuid
from django.core.cache import cache
from django.db import transaction
from asgiref.sync import async_to_sync
import logging

User = get_user_model()

class ConversionTask(models.Model):
    """文件转换任务模型"""
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    original_file = models.FileField(upload_to='uploads/%Y/%m/%d/', verbose_name=_('Original File'))
    converted_file = models.FileField(upload_to='converted/%Y/%m/%d/', null=True, blank=True, verbose_name=_('Converted File'))
    original_format = models.CharField(max_length=10, verbose_name=_('Original Format'))
    target_format = models.CharField(max_length=10, verbose_name=_('Target Format'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('Status'))
    error_message = models.TextField(null=True, blank=True, verbose_name=_('Error Message'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    processing_time = models.DurationField(null=True, blank=True, verbose_name=_('Processing Time'))
    file_size = models.BigIntegerField(default=0, verbose_name=_('File Size'))
    retry_count = models.IntegerField(default=0, verbose_name=_('Retry Count'))
    progress = models.IntegerField(
        default=0,
        verbose_name=_('Progress')
    )

    class Meta:
        verbose_name = _('Conversion Task')
        verbose_name_plural = _('Conversion Tasks')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_format} -> {self.target_format} ({self.status})"

    def update_progress(self, progress):
        """更新进度(添加锁机制)"""
        with transaction.atomic():
            # 获取锁
            task = ConversionTask.objects.select_for_update().get(id=self.id)
            task.progress = progress
            task.save()
            
            # 更新缓存
            cache.set(f'task_progress:{self.id}', progress, 300)
            
            # 发送进度通知
            self._notify_progress_update()
            
    def _notify_progress_update(self):
        """发送进度更新通知"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'task_{self.id}',
                {
                    'type': 'conversion_progress',
                    'task_id': self.id,
                    'progress': self.progress,
                    'status': self.status
                }
            )
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")

    def get_progress(self):
        """获取进度"""
        from .utils import get_task_progress
        return get_task_progress(self.id)

    def update_status(self, status, error_message=None):
        """更新状态"""
        with transaction.atomic():
            task = ConversionTask.objects.select_for_update().get(id=self.id)
            task.status = status
            if error_message:
                task.error_message = error_message
            task.save()
            
            # 清除缓存
            from .utils import invalidate_task_cache
            invalidate_task_cache(self.id)

class ConversionHistory(models.Model):
    """转换历史记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    task = models.ForeignKey(ConversionTask, on_delete=models.CASCADE, verbose_name=_('Task'))
    ip_address = models.GenericIPAddressField(verbose_name=_('IP Address'))
    user_agent = models.TextField(verbose_name=_('User Agent'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Conversion History')
        verbose_name_plural = _('Conversion Histories')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"

class UploadSession(models.Model):
    """文件上传会话"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    session_id = models.CharField(max_length=100, unique=True, verbose_name=_('Session ID'))
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    file_size = models.BigIntegerField(verbose_name=_('File Size'))
    chunk_size = models.IntegerField(verbose_name=_('Chunk Size'))
    total_chunks = models.IntegerField(verbose_name=_('Total Chunks'))
    uploaded_chunks = models.JSONField(default=list, verbose_name=_('Uploaded Chunks'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    expires_at = models.DateTimeField(verbose_name=_('Expires At'))
    completed = models.BooleanField(default=False, verbose_name=_('Completed'))

    class Meta:
        verbose_name = _('Upload Session')
        verbose_name_plural = _('Upload Sessions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.session_id})"

    @property
    def is_expired(self):
        """检查会话是否过期"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def progress(self):
        """计算上传进度"""
        return len(self.uploaded_chunks) / self.total_chunks * 100

class PreviewTask(models.Model):
    """预览任务模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conversion_task = models.ForeignKey(ConversionTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ConversionTask.STATUS_CHOICES)
    preview_file = models.FileField(upload_to='previews/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class ConversionStatistics(models.Model):
    """转换统计模型"""
    cpu_usage = models.FloatField(
        verbose_name=_('CPU Usage')
    )
    memory_usage = models.FloatField(
        verbose_name=_('Memory Usage')
    )
    task_count = models.IntegerField(
        verbose_name=_('Task Count')
    )
    error_count = models.IntegerField(
        verbose_name=_('Error Count')
    )
    average_processing_time = models.DurationField(
        verbose_name=_('Average Processing Time')
    )
    response_time = models.FloatField(
        verbose_name=_('Response Time'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    class Meta:
        verbose_name = _('Conversion Statistics')
        verbose_name_plural = _('Conversion Statistics')
        ordering = ['-created_at']

    def __str__(self):
        return f"Stats - {self.created_at}"