"""用户认证表单"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, EmailValidator
from .models import User, UserProfile

class UserRegistrationForm(UserCreationForm):
    """用户注册表单"""
    email = forms.EmailField(
        label=_('Email'),
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email')
        })
    )
    
    username = forms.CharField(
        label=_('Username'),
        min_length=3,
        max_length=30,
        validators=[MinLengthValidator(3)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Choose a username')
        })
    )
    
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter password')
        })
    )
    
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm password')
        })
    )
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')
        
    def clean_email(self):
        """验证邮箱"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('This email is already registered.'))
        return email
        
    def clean_username(self):
        """验证用户名"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('This username is already taken.'))
        return username

class UserLoginForm(forms.Form):
    """用户登录表单"""
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email')
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter password')
        })
    )
    
    remember_me = forms.BooleanField(
        label=_('Remember me'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

class UserProfileForm(forms.ModelForm):
    """用户资料表单"""
    class Meta:
        model = UserProfile
        fields = [
            'avatar',
            'bio',
            'language',
            'timezone',
            'email_notifications',
            'conversion_notifications'
        ]
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'language': forms.Select(attrs={
                'class': 'form-select'
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-select'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'conversion_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

class ChangePasswordForm(PasswordChangeForm):
    """修改密码表单"""
    old_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter current password')
        })
    )
    
    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new password')
        })
    )
    
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password')
        })
    )

class EmailVerificationForm(forms.Form):
    """邮箱验证表单"""
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email')
        })
    )
    
    def clean_email(self):
        """验证邮箱"""
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_verified:
                raise forms.ValidationError(_('This email is already verified.'))
            return email
        except User.DoesNotExist:
            raise forms.ValidationError(_('No user found with this email.')) 