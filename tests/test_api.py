"""API接口测试"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.converter.models import ConversionTask
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class APITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_api_authentication(self):
        """测试API认证"""
        # 未认证访问
        client = APIClient()
        response = client.get(reverse('api:task-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Token认证
        token = self.user.auth_token.key
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = client.get(reverse('api:task-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_task_list_api(self):
        """测试任务列表API"""
        # 创建测试任务
        tasks = []
        for i in range(3):
            task = ConversionTask.objects.create(
                user=self.user,
                original_file=f'test{i}.txt',
                original_format='txt',
                target_format='pdf'
            )
            tasks.append(task)

        # 获取任务列表
        response = self.client.get(reverse('api:task-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

        # 测试分页
        response = self.client.get(reverse('api:task-list') + '?page_size=2')
        self.assertEqual(len(response.data['results']), 2)

    def test_task_detail_api(self):
        """测试任务详情API"""
        task = ConversionTask.objects.create(
            user=self.user,
            original_file='test.txt',
            original_format='txt',
            target_format='pdf'
        )

        # 获取任务详情
        response = self.client.get(reverse('api:task-detail', args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(task.id))

        # 测试其他用户无法��问
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(reverse('api:task-detail', args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_file_upload_api(self):
        """测试文件上传API"""
        # 创建测试文件
        file = SimpleUploadedFile(
            "test.txt",
            b"Test content",
            content_type="text/plain"
        )

        # 上传文件
        response = self.client.post(
            reverse('api:upload'),
            {
                'file': file,
                'target_format': 'pdf'
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('task_id', response.data)

        # 验证任务创建
        task_id = response.data['task_id']
        task = ConversionTask.objects.get(id=task_id)
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.original_format, 'txt')
        self.assertEqual(task.target_format, 'pdf')

    def test_batch_conversion_api(self):
        """测试批量转换API"""
        # 创建测试文件
        files = [
            SimpleUploadedFile(
                f"test{i}.txt",
                b"Test content",
                content_type="text/plain"
            ) for i in range(3)
        ]

        # 批量上传
        response = self.client.post(
            reverse('api:batch-upload'),
            {
                'files': files,
                'target_format': 'pdf'
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('batch_id', response.data)
        self.assertEqual(len(response.data['tasks']), 3)

    def test_api_rate_limiting(self):
        """测试API速率限制"""
        # 连续发送大量请求
        for i in range(101):  # 假设限制是100次/小时
            response = self.client.get(reverse('api:task-list'))
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        else:
            self.fail('Rate limit not enforced')

    def test_api_error_handling(self):
        """测试API错误处理"""
        # 测试无效的请求数据
        response = self.client.post(
            reverse('api:upload'),
            {'target_format': 'invalid'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 测试不存在的资源
        response = self.client.get(
            reverse('api:task-detail', args=['invalid-id'])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 测试方法不允许
        response = self.client.delete(reverse('api:task-list'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_api_filtering_sorting(self):
        """测试API过滤和排序"""
        # 创建测试数据
        statuses = ['completed', 'failed', 'pending']
        for status in statuses:
            ConversionTask.objects.create(
                user=self.user,
                original_file='test.txt',
                original_format='txt',
                target_format='pdf',
                status=status
            )

        # 测试状态过滤
        response = self.client.get(reverse('api:task-list') + '?status=completed')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'completed')

        # 测试排序
        response = self.client.get(reverse('api:task-list') + '?ordering=-created_at')
        tasks = response.data['results']
        self.assertTrue(all(
            tasks[i]['created_at'] >= tasks[i+1]['created_at']
            for i in range(len(tasks)-1)
        )) 