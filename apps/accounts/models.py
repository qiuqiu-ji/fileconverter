"""用户账户模型"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
import uuid

class UserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, email, password=None, **extra_fields):
        """创建普通用户"""
        if not email:
            raise ValueError(_('Email address is required'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def create_superuser(self, email, password=None, **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))
            
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """自定义用户模型"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('Email address'), unique=True)
    username = models.CharField(
        _('Username'),
        max_length=30,
        unique=True,
        validators=[MinLengthValidator(3)]
    )
    
    # 用户配额和限制
    daily_conversion_limit = models.IntegerField(
        _('Daily conversion limit'),
        default=100
    )
    storage_quota = models.BigIntegerField(
        _('Storage quota (bytes)'),
        default=1073741824  # 1GB
    )
    
    # 用户状态
    is_active = models.BooleanField(_('Active'), default=True)
    is_verified = models.BooleanField(_('Email verified'), default=False)
    
    # 时间戳
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    last_login_at = models.DateTimeField(_('Last login at'), null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
        
    def __str__(self):
        return self.email
        
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
        
    def get_short_name(self):
        return self.username

class UserProfile(models.Model):
    """用户配置文件"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # 个人信息
    avatar = models.ImageField(
        _('Avatar'),
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True
    )
    bio = models.TextField(_('Bio'), max_length=500, blank=True)
    
    # 偏好设置
    language = models.CharField(
        _('Preferred language'),
        max_length=10,
        default='zh-hans'
    )
    timezone = models.CharField(
        _('Timezone'),
        max_length=50,
        default='Asia/Shanghai'
    )
    
    # 通知设置
    email_notifications = models.BooleanField(
        _('Email notifications'),
        default=True
    )
    conversion_notifications = models.BooleanField(
        _('Conversion notifications'),
        default=True
    )
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        
    def __str__(self):
        return f"{self.user.username}'s profile" 