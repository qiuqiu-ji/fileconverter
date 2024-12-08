"""账户相关测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()

class UserRegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }

    def test_register_page(self):
        """测试注册页面是否可访问"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_success(self):
        """测试成功注册"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())
        
        # 检查用户配���文件是否创建
        user = User.objects.get(email=self.user_data['email'])
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)

    def test_register_invalid_email(self):
        """测试无效邮箱"""
        self.user_data['email'] = 'invalid-email'
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')

    def test_register_duplicate_email(self):
        """测试重复邮箱"""
        User.objects.create_user(
            email=self.user_data['email'],
            username='existinguser',
            password='existingpass123'
        )
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'This email is already registered.')

class UserLoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_login_page(self):
        """测试登录页面是否可访问"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_success(self):
        """测试成功登录"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('converter:home'))

    def test_login_wrong_password(self):
        """测试密码错误"""
        response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', None, 'Invalid email or password.')

class UserProfileTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.profile_url = reverse('accounts:profile')
        self.client.login(email=self.user_data['email'], password=self.user_data['password'])

    def test_profile_page(self):
        """测试个人资料页面是否可访问"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')

    def test_update_profile(self):
        """测试更新个人资料"""
        data = {
            'language': 'en',
            'timezone': 'UTC',
            'email_notifications': True,
            'conversion_notifications': False
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        
        # 检查更新是否成功
        profile = self.user.profile
        self.assertEqual(profile.language, data['language'])
        self.assertEqual(profile.timezone, data['timezone'])
        self.assertEqual(profile.email_notifications, data['email_notifications'])
        self.assertEqual(profile.conversion_notifications, data['conversion_notifications'])

class PasswordChangeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.change_password_url = reverse('accounts:change_password')
        self.client.login(email=self.user_data['email'], password=self.user_data['password'])

    def test_change_password_page(self):
        """测试修改密码页面是否可访问"""
        response = self.client.get(self.change_password_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/change_password.html')

    def test_change_password_success(self):
        """测试成功修改密码"""
        data = {
            'old_password': self.user_data['password'],
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 302)
        
        # 检查是否可以使用新密码登录
        self.client.logout()
        login_success = self.client.login(
            email=self.user_data['email'],
            password=data['new_password1']
        )
        self.assertTrue(login_success)

    def test_change_password_wrong_old(self):
        """测试旧密码错误"""
        data = {
            'old_password': 'wrongpass',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'old_password', 'Your old password was entered incorrectly.') 