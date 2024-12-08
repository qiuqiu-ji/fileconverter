from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from rest_framework.routers import DefaultRouter
from apps.converter import api_views, api_docs
from apps.converter import upload_views
from apps.converter import preview_views
from django.views.generic import RedirectView
from apps.converter.api import ConversionTaskViewSet

router = DefaultRouter()
router.register(r'conversions', api_views.ConversionViewSet, basename='conversion')
router.register(r'tasks', ConversionTaskViewSet, basename='task')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API URLs
    path('api/v1/', include(router.urls)),
    path('api/v1/docs/', api_docs.api_documentation, name='api-docs'),
    
    # 文件上传
    path('api/upload/create-session', upload_views.create_upload_session, name='create_upload_session'),
    path('api/upload/chunk', upload_views.upload_chunk, name='upload_chunk'),
    path('api/upload/complete', upload_views.complete_upload, name='complete_upload'),
    
    # 文件预览
    path('api/preview/generate/', preview_views.generate_preview, name='generate_preview'),
    path('api/preview/<str:filename>/', preview_views.view_preview, name='view_preview'),
    
    # 应用路由
    path('accounts/', include('apps.accounts.urls')),
    path('converter/', include('apps.converter.urls')),
    
    # API路由
    path('api/accounts/', include('apps.accounts.api_urls')),
    path('api/converter/', include('apps.converter.api_urls')),
    
    # 首页重定向
    path('', RedirectView.as_view(url='/converter/', permanent=False)),
]

# 国际化URL
urlpatterns += i18n_patterns(
    path('', include('apps.converter.urls')),
    prefix_default_language=False
)

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 
    
    # 调试工具栏
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ] 