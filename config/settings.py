"""
Django项目配置
"""
import os
from pathlib import Path
from datetime import timedelta

# 构建路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 安全设置
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-secret-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') + ['localhost', '127.0.0.1', '.vercel.app']

# 应用定义
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 第三方应用
    'rest_framework',
    'channels',
    'celery',
    'django_cleanup',
    
    # 自定义应用
    'apps.accounts',
    'apps.converter',
    'apps.security',
]

# 中间件
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.security.middleware.FileUploadSecurityMiddleware',
    'apps.security.middleware.SecurityHeadersMiddleware',
    'apps.core.middleware.ErrorHandlerMiddleware',
    'apps.core.middleware.MaintenanceModeMiddleware',
]

ROOT_URLCONF = 'config.urls'

# 模板配置
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.error_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'fileconverter'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 5,
        }
    }
}

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            }
        }
    }
}

# Celery配置
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/2')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'

# Channels配置
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://localhost:6379/3')],
        },
    },
}

# 认证配置
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'converter:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 国际化配置
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('zh-hans', '简体中文'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 文件上传配置
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_FILES = 20
FILE_UPLOAD_MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_MAX_REQUESTS_PER_HOUR = 100

# 支持的文件格式
ALLOWED_FILE_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'svg': 'image/svg+xml',
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'txt': 'text/plain',
    'csv': 'text/csv',
}

# 邮件配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# 安全设置
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# REST Framework配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# 站点配置
SITE_NAME = 'File Converter'
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# 错误处理相关配置
MIDDLEWARE += [
    'apps.core.middleware.ErrorHandlerMiddleware',
    'apps.core.middleware.MaintenanceModeMiddleware',
]

# 维护模式配置
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', default=False)
MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', default=None)
MAINTENANCE_START_TIME = os.environ.get('MAINTENANCE_START_TIME', default=None)
MAINTENANCE_DURATION = os.environ.get('MAINTENANCE_DURATION', default=None)
MAINTENANCE_END_TIME = os.environ.get('MAINTENANCE_END_TIME', default=None)

# 允许的维护模式IP
MAINTENANCE_ALLOWED_IPS = os.environ.get('MAINTENANCE_ALLOWED_IPS', default=[]).split(',')

# 维护模式排除URL
MAINTENANCE_EXCLUDE_URLS = [
    r'^/admin/',
    r'^/static/',
    r'^/media/',
    r'^/maintenance/',
    r'^/health/',
    r'^/api/status/',
]

# 错误页面模板配置
handler403 = 'apps.core.views.error_403'
handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500'

# 文件转换配置
CONVERSION_SETTINGS = {
    'chunk_size': 1024 * 1024,  # 1MB
    'max_file_size': 100 * 1024 * 1024,  # 100MB
    'supported_formats': ['pdf', 'docx', 'txt'],
    'temp_dir': '/tmp/conversions',
    'preview': {
        'max_size': 50 * 1024 * 1024,  # 50MB
        'timeout': 30,  # 30秒
        'thumbnail_size': (800, 800)
    },
    'batch': {
        'max_files': 10,
        'max_total_size': 500 * 1024 * 1024,  # 500MB
        'timeout': 3600  # 1小时
    },
    'quality': {
        'default_dpi': 300,
        'default_quality': 95,
        'max_dimension': 4096
    },
    'storage': {
        'temp_dir': '/tmp/conversions',
        'archive_dir': 'archives',
        'cleanup_interval': 3600  # 1小时
    }
}

# 配额设置
QUOTA_SETTINGS = {
    'cache_timeout': 3600,  # 1小时
    'notification_cooldown': 86400,  # 24小时
    'max_file_size': 100 * 1024 * 1024,  # 100MB
    'max_total_size': 1024 * 1024 * 1024,  # 1GB
    'alert_thresholds': {
        'low': 0.2,
        'critical': 0.1
    },
    'plans': {
        'free': {
            'name': '免费版',
            'conversions': 10,
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'concurrent_tasks': 1,
            'formats': ['pdf', 'txt', 'docx'],
            'features': ['basic_conversion']
        },
        'basic': {
            'name': '基础版',
            'conversions': 50,
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'concurrent_tasks': 3,
            'formats': ['pdf', 'txt', 'docx', 'xlsx', 'pptx'],
            'features': ['basic_conversion', 'batch_conversion']
        },
        'premium': {
            'name': '高级版',
            'conversions': 100,
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'concurrent_tasks': 5,
            'formats': ['pdf', 'txt', 'docx', 'xlsx', 'pptx', 'jpg', 'png'],
            'features': ['basic_conversion', 'batch_conversion', 'priority_queue']
        }
    }
}