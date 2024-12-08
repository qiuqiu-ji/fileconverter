"""安全相关模型"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

User = get_user_model()

class SecurityLog(models.Model):
    """安全日志模型"""
    LEVEL_CHOICES = [
        ('INFO', _('Info')),
        ('WARNING', _('Warning')),
        ('ERROR', _('Error')),
    ]

    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        verbose_name=_('Log Level')
    )
    message = models.TextField(
        verbose_name=_('Log Message')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('User')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    class Meta:
        verbose_name = _('Security Log')
        verbose_name_plural = _('Security Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.level} - {self.created_at}"

class SecurityAlert(models.Model):
    """安全告警模型"""
    SEVERITY_CHOICES = [
        ('LOW', _('Low')),
        ('MEDIUM', _('Medium')),
        ('HIGH', _('High')),
        ('CRITICAL', _('Critical')),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name=_('Alert Title')
    )
    description = models.TextField(
        verbose_name=_('Alert Description')
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        verbose_name=_('Severity Level')
    )
    source = models.CharField(
        max_length=50,
        verbose_name=_('Alert Source')
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_('Is Resolved')
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('Resolved By')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Security Alert')
        verbose_name_plural = _('Security Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'is_resolved']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.severity} - {self.title}" 

class BlockedIP(models.Model):
    """IP封禁记录"""
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address'),
        unique=True
    )
    reason = models.CharField(
        max_length=200,
        verbose_name=_('Blocking Reason')
    )
    blocked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Blocked At')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires At')
    )
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_ips',
        verbose_name=_('Blocked By')
    )
    is_permanent = models.BooleanField(
        default=False,
        verbose_name=_('Is Permanent')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    attempts_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Failed Attempts Count')
    )

    class Meta:
        verbose_name = _('Blocked IP')
        verbose_name_plural = _('Blocked IPs')
        ordering = ['-blocked_at']
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['blocked_at']),
        ]

    def __str__(self):
        return f"{self.ip_address} ({self.reason})"

    @property
    def is_active(self):
        """检查封禁是否有效"""
        if self.is_permanent:
            return True
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True

    def extend_block(self, hours=24):
        """延长封禁时间"""
        if self.expires_at:
            self.expires_at = max(
                self.expires_at,
                timezone.now() + timezone.timedelta(hours=hours)
            )
        else:
            self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        self.save()

class AuditLog(models.Model):
    """审计日��"""
    ACTION_TYPES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('file_upload', _('File Upload')),
        ('file_download', _('File Download')),
        ('file_delete', _('File Delete')),
        ('settings_change', _('Settings Change')),
        ('permission_change', _('Permission Change')),
        ('ip_block', _('IP Block')),
        ('ip_unblock', _('IP Unblock')),
        ('other', _('Other')),
    ]

    SEVERITY_LEVELS = [
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('critical', _('Critical')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name=_('Action Type')
    )
    action_detail = models.TextField(
        verbose_name=_('Action Detail')
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='info',
        verbose_name=_('Severity Level')
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    user_agent = models.TextField(
        verbose_name=_('User Agent')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    status = models.CharField(
        max_length=20,
        default='success',
        verbose_name=_('Status')
    )
    resource_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Resource Type')
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Resource ID')
    )
    extra_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Extra Data')
    )

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['severity']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]

    def __str__(self):
        return f"{self.action_type} by {self.user} at {self.created_at}"

    @classmethod
    def log(cls, request, action_type, detail, severity='info', **kwargs):
        """记录审计日志"""
        return cls.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action_type=action_type,
            action_detail=detail,
            severity=severity,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            **kwargs
        ) 

class PerformanceAlert(models.Model):
    """性能报警"""
    type = models.CharField(
        max_length=50,
        verbose_name=_('Alert Type')
    )
    data = models.JSONField(
        verbose_name=_('Alert Data')
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Timestamp')
    )
    resolved = models.BooleanField(
        default=False,
        verbose_name=_('Resolved')
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    resolved_by = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name=_('Resolved By')
    )
    resolution_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Resolution Notes')
    )
    threshold = models.FloatField(
        verbose_name=_('Threshold Value')
    )
    current_value = models.FloatField(
        verbose_name=_('Current Value')
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_('Duration')
    )

    class Meta:
        verbose_name = _('Performance Alert')
        verbose_name_plural = _('Performance Alerts')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['type', 'timestamp']),
            models.Index(fields=['resolved', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.type} ({self.current_value}/{self.threshold}) - {self.timestamp}"

    def mark_resolved(self, user, notes=None):
        """标记为已解决"""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        if notes:
            self.resolution_notes = notes
        self.save()

    @property
    def duration_str(self):
        """获取持续时间字符串"""
        if not self.duration:
            return ''
        hours = self.duration.total_seconds() / 3600
        return f"{hours:.1f} hours" 