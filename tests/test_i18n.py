"""国际化和本地化测试"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import translation
from django.conf import settings
from apps.accounts.models import User

class I18nTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_language_switch(self):
        """测试语言切换"""
        # 默认语言
        response = self.client.get(reverse('converter:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '文件转换器')

        # 切换到英文
        with translation.override('en'):
            response = self.client.get(reverse('converter:home'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'File Converter')

    def test_date_format(self):
        """测试日期格式本地化"""
        from django.utils import timezone
        import datetime
        
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf',
            created_at=timezone.now()
        )

        # 中文日期格式
        response = self.client.get(reverse('converter:history'))
        self.assertContains(response, task.created_at.strftime('%Y年%m月%d日'))

        # 英文日期格式
        with translation.override('en'):
            response = self.client.get(reverse('converter:history'))
            self.assertContains(
                response, 
                task.created_at.strftime('%b %d, %Y')
            )

    def test_error_messages(self):
        """测试错误消息翻译"""
        # 上传无效文件
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b"Invalid file",
            content_type="application/x-msdownload"
        )

        # 中文错误消息
        response = self.client.post(reverse('converter:upload_session'), {
            'file': invalid_file
        })
        self.assertContains(response, '不支持的文件类型', status_code=400)

        # 英文错误消息
        with translation.override('en'):
            response = self.client.post(reverse('converter:upload_session'), {
                'file': invalid_file
            })
            self.assertContains(response, 'Unsupported file type', status_code=400)

    def test_timezone_handling(self):
        """测试时区处理"""
        # 创建测试任务
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        # 设置用户时区为上海
        self.user.profile.timezone = 'Asia/Shanghai'
        self.user.profile.save()

        response = self.client.get(reverse('converter:history'))
        self.assertEqual(response.status_code, 200)
        # 验证时间显示是否符合用户时区

        # 设置用户时区为纽约
        self.user.profile.timezone = 'America/New_York'
        self.user.profile.save()

        response = self.client.get(reverse('converter:history'))
        self.assertEqual(response.status_code, 200)
        # 验证时间显示是否符合用户时区 