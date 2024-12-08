"""用户管理员配置"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """自定义用户管理"""
    list_display = ('email', 'username', 'is_active', 'is_verified', 'created_at')
    list_filter = ('is_active', 'is_verified', 'is_staff')
    search_fields = ('email', 'username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_verified',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Quotas'), {
            'fields': ('daily_conversion_limit', 'storage_quota')
        }),
        (_('Important dates'), {
            'fields': ('last_login_at', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """用户配置文件管理"""
    list_display = ('user', 'language', 'timezone')
    list_filter = ('language', 'timezone')
    search_fields = ('user__email', 'user__username')
    
    fieldsets = (
        (_('User'), {'fields': ('user', 'avatar', 'bio')}),
        (_('Preferences'), {
            'fields': ('language', 'timezone')
        }),
        (_('Notifications'), {
            'fields': ('email_notifications', 'conversion_notifications')
        }),
    ) 