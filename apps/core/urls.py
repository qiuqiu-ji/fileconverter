"""核心应用URL配置"""
from django.urls import path
from django.conf import settings
from . import views

app_name = 'core'

urlpatterns = [
    path('maintenance/', views.maintenance, name='maintenance'),
]

if settings.DEBUG:
    urlpatterns += [
        path('error-test/', views.error_test, name='error_test'),
    ]

# 错误处理器
handler403 = 'apps.core.views.error_403'
handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500' 