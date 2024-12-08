"""用户应用配置"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AccountsConfig(AppConfig):
    """用户应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = _('User Accounts')
    
    def ready(self):
        """应用就绪时的操作"""
        import apps.accounts.signals  # 导入信号处理器 