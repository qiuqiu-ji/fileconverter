"""安全应用URL配置"""
from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    path('logs/', views.security_logs, name='logs'),
    path('alerts/', views.security_alerts, name='alerts'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    path('stats/', views.security_stats, name='stats'),
] 