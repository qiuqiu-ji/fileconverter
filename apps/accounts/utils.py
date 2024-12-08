"""用户认证工具函数"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.conf import settings
from django.utils.crypto import get_random_string
import jwt
from datetime import datetime, timedelta

def generate_verification_token(user):
    """生成邮箱验证令牌"""
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """验证令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def send_verification_email(user):
    """发送验证邮件"""
    token = generate_verification_token(user)
    verification_url = f"{settings.SITE_URL}/accounts/verify-email/{token}"
    
    context = {
        'user': user,
        'verification_url': verification_url
    }
    
    html_message = render_to_string('accounts/emails/verify_email.html', context)
    plain_message = render_to_string('accounts/emails/verify_email.txt', context)
    
    send_mail(
        subject=_('Verify your email address'),
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

def send_password_reset_email(user):
    """发送密码重置邮件"""
    token = generate_verification_token(user)
    reset_url = f"{settings.SITE_URL}/accounts/reset-password/{token}"
    
    context = {
        'user': user,
        'reset_url': reset_url
    }
    
    html_message = render_to_string('accounts/emails/reset_password.html', context)
    plain_message = render_to_string('accounts/emails/reset_password.txt', context)
    
    send_mail(
        subject=_('Reset your password'),
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

def generate_temp_password():
    """生成临时密码"""
    return get_random_string(12) 