"""安全应用管理界面"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import SecurityLog, SecurityAlert, PerformanceAlert
from django.utils import timezone

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'type', 'source_ip', 'user', 'action']
    list_filter = ['type', 'timestamp', 'source_ip']
    search_fields = ['source_ip', 'user', 'description']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']

@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'type', 'severity', 'resolved']
    list_filter = ['type', 'severity', 'resolved', 'timestamp']
    search_fields = ['description', 'data']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    actions = ['mark_resolved']

    def mark_resolved(self, request, queryset):
        queryset.update(
            resolved=True,
            resolved_by=request.user.username,
            resolved_at=timezone.now()
        )
    mark_resolved.short_description = _("Mark selected alerts as resolved")

@admin.register(PerformanceAlert)
class PerformanceAlertAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'type', 'current_value', 'threshold', 'resolved']
    list_filter = ['type', 'resolved', 'timestamp']
    search_fields = ['type', 'data']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'duration_str']
    actions = ['mark_resolved']

    def mark_resolved(self, request, queryset):
        queryset.update(
            resolved=True,
            resolved_by=request.user.username,
            resolved_at=timezone.now()
        )
    mark_resolved.short_description = _("Mark selected alerts as resolved") 