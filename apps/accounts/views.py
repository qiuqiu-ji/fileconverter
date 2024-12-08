"""用户认证视图"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

from .forms import (
    UserRegistrationForm, 
    UserLoginForm,
    UserProfileForm,
    ChangePasswordForm,
    EmailVerificationForm
)
from .models import User, UserProfile
from .utils import send_verification_email, generate_verification_token
from apps.security.decorators import rate_limit, log_access
from apps.security.logging import FileConverterLogger

logger = FileConverterLogger()

@rate_limit('register', limit=5, period=3600)
@log_access('user_register')
def register_view(request):
    """用户注册视图"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # 创建用户
                user = form.save(commit=False)
                user.is_active = True
                user.save()
                
                # 创建用户配置文件
                UserProfile.objects.create(user=user)
                
                # 发送验证邮件
                send_verification_email(user)
                
                messages.success(request, _('Registration successful. Please verify your email.'))
                return redirect('accounts:login')
                
            except Exception as e:
                logger.log_error('registration_error', str(e))
                messages.error(request, _('Registration failed. Please try again.'))
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = UserRegistrationForm()
        
    return render(request, 'accounts/register.html', {'form': form})

@rate_limit('login', limit=10, period=3600)
@log_access('user_login')
def login_view(request):
    """用户登录视图"""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(email=email, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # 更新最后登录时间和IP
                    user.last_login_at = timezone.now()
                    user.save()
                    
                    logger.log_audit(
                        'user_login',
                        user,
                        {'ip': request.META.get('REMOTE_ADDR')}
                    )
                    
                    return redirect('converter:home')
                else:
                    messages.error(request, _('Your account is inactive.'))
            else:
                messages.error(request, _('Invalid email or password.'))
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {'form': form})

@login_required
@log_access('user_logout')
def logout_view(request):
    """用户登出视图"""
    logger.log_audit('user_logout', request.user, {})
    logout(request)
    messages.success(request, _('You have been logged out.'))
    return redirect('accounts:login')

@login_required
def profile_view(request):
    """用户个人资料视图"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user.profile)
        
    return render(request, 'accounts/profile.html', {
        'form': form,
        'user': request.user
    })

@login_required
def change_password_view(request):
    """修改密码视图"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _('Password changed successfully.'))
            
            # 记录密码修改
            logger.log_audit(
                'password_change',
                user,
                {'ip': request.META.get('REMOTE_ADDR')}
            )
            
            return redirect('accounts:login')
    else:
        form = ChangePasswordForm(request.user)
        
    return render(request, 'accounts/change_password.html', {'form': form})

@require_http_methods(['GET'])
def verify_email(request, token):
    """邮箱验证视图"""
    try:
        user = User.objects.get(verification_token=token)
        if not user.is_verified:
            user.is_verified = True
            user.verification_token = None
            user.save()
            messages.success(request, _('Email verified successfully.'))
        else:
            messages.info(request, _('Email already verified.'))
    except User.DoesNotExist:
        messages.error(request, _('Invalid verification token.'))
        
    return redirect('accounts:login')

@login_required
def resend_verification_email(request):
    """重新发送验证邮件"""
    if not request.user.is_verified:
        try:
            send_verification_email(request.user)
            messages.success(request, _('Verification email sent.'))
        except Exception as e:
            logger.log_error('email_send_error', str(e))
            messages.error(request, _('Failed to send verification email.'))
    else:
        messages.info(request, _('Email already verified.'))
        
    return redirect('accounts:profile') 