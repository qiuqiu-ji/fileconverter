from django.urls import path
from . import views
from . import api_views
from . import upload_views
from . import preview_views

app_name = 'converter'

urlpatterns = [
    # 页面路由
    path('', views.home, name='home'),
    path('convert/', views.convert_page, name='convert_page'),
    path('history/', views.conversion_history, name='history'),
    
    # 文件处理路由
    path('upload/session/', views.create_upload_session, name='upload_session'),
    path('upload/chunk/', views.upload_chunk, name='chunk_upload'),
    path('upload/complete/', views.complete_upload, name='complete_upload'),
    path('download/<uuid:task_id>/', views.download_converted_file, name='download'),
    
    # 批量处理路由
    path('batch/create/', views.create_batch_task, name='batch_create'),
    path('batch/upload/', views.batch_upload_file, name='batch_upload'),
    path('batch/start/', views.start_batch_conversion, name='batch_start'),
    path('batch/status/<uuid:batch_id>/', views.batch_status, name='batch_status'),
    
    # API路由
    path('api/formats/', api_views.supported_formats, name='supported_formats'),
    path('api/convert/', api_views.convert_file, name='api_convert'),
    path('api/batch/', api_views.batch_convert, name='api_batch_convert'),
    
    # 预览路由
    path('preview/<uuid:task_id>/', views.preview_file, name='preview'),
    path('preview/status/<uuid:preview_id>/', views.preview_status, name='preview_status'),
]

# WebSocket路由在 routing.py 中定义 