"""错误页面上下文处理器"""
from django.conf import settings
from django.utils.translation import gettext as _

def error_context(request):
    """添加错误页面相关上下文"""
    return {
        'site_name': getattr(settings, 'SITE_NAME', 'File Converter'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', None),
        'company_name': getattr(settings, 'COMPANY_NAME', 'Our Company'),
        'maintenance_mode': getattr(settings, 'MAINTENANCE_MODE', False),
        'error_messages': {
            403: _('You do not have permission to access this page.'),
            404: _('The page you are looking for does not exist.'),
            500: _('An unexpected error occurred. Our team has been notified.'),
            503: _('The system is currently under maintenance. Please try again later.')
        }
    } 