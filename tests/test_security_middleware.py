"""安全中间件测试"""
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings
from apps.security.models import BlockedIP, AuditLog
from apps.security.middleware import SecurityMiddleware
import json
from django.utils import timezone

User = get_user_model()

class SecurityMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.middleware = SecurityMiddleware(lambda r: None)

    def test_blocked_ip(self):
        """测试IP封禁"""
        # 创建封禁记录
        BlockedIP.objects.block_ip('127.0.0.1', 'Test blocking')
        
        # 尝试访问
        response = self.client.get('/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode(), 'IP blocked')

        # 验证日志记录
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action_type, 'error')
        self.assertEqual(log.ip_address, '127.0.0.1')

    @override_settings(SECURITY_RATE_LIMITS={'default': '2/m'})
    def test_rate_limit(self):
        """测试请求频率限制"""
        # 前两次请求应该成功
        for _ in range(2):
            request = self.factory.get('/')
            response = self.middleware(request)
            self.assertIsNone(response)
        
        # 第三次请求应该被限制
        request = self.factory.get('/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode(), 'Rate limit exceeded')

    @override_settings(SECURITY_URL_WHITELIST=[r'^/health/$'])
    def test_whitelist(self):
        """测试白名单"""
        # 封禁IP
        BlockedIP.objects.block_ip('127.0.0.1', 'Test blocking')
        
        # 白名单URL应该可以访问
        request = self.factory.get('/health/')
        response = self.middleware(request)
        self.assertIsNone(response)
        
        # 其他URL应该被封禁
        request = self.factory.get('/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_request_logging(self):
        """测试请求日志记录"""
        # 创建带认证的请求
        request = self.factory.get('/test/')
        request.user = self.user
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        # 处理请求
        self.middleware(request)
        
        # 验证日志
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action_type, 'request')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.user_agent, 'Mozilla/5.0')
        self.assertEqual(log.extra_data['path'], '/test/')

    def test_error_response_logging(self):
        """测试错误响应日志记录"""
        # 创建一个返回错误的中间件
        error_middleware = SecurityMiddleware(lambda r: type('Response', (), {'status_code': 500}))
        
        # 处理请求
        request = self.factory.get('/error/')
        error_middleware(request)
        
        # 验证错误日志
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action_type, 'error')
        self.assertEqual(log.severity, 'error')
        self.assertEqual(log.extra_data['status_code'], 500)

    @override_settings(
        SECURITY_RATE_PATTERNS={r'^/api/': 'api', r'^/login/$': 'login'},
        SECURITY_RATE_LIMITS={'api': '100/h', 'login': '5/m', 'default': '50/h'}
    )
    def test_custom_rate_patterns(self):
        """测试自定义频率限制模式"""
        # API请求
        for _ in range(6):
            request = self.factory.get('/api/status/')
            response = self.middleware(request)
            self.assertIsNone(response)
        
        # 登录请求
        for i in range(6):
            request = self.factory.post('/login/')
            response = self.middleware(request)
            if i < 5:
                self.assertIsNone(response)
            else:
                self.assertEqual(response.status_code, 403)

    def test_parse_rate_limit(self):
        """测试频率限制解析"""
        test_cases = [
            ('10/s', (10, 1)),
            ('5/m', (5, 60)),
            ('100/h', (100, 3600)),
            ('1000/d', (1000, 86400)),
            ('50/x', (50, 3600)),  # 无效单位应该使用默认值
        ]
        
        for limit, expected in test_cases:
            count, period = self.middleware._parse_rate_limit(limit)
            self.assertEqual((count, period), expected)

    def test_client_ip_detection(self):
        """测试客户端IP检测"""
        # 直接IP
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(
            self.middleware._get_client_ip(request),
            '192.168.1.1'
        )
        
        # X-Forwarded-For
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2'
        self.assertEqual(
            self.middleware._get_client_ip(request),
            '10.0.0.1'
        )

    def test_request_filtering(self):
        """测试请求过滤"""
        test_cases = [
            ('/static/css/main.css', False),
            ('/media/uploads/file.pdf', False),
            ('/health/', False),
            ('/api/status/', True),
            ('/', True),
        ]
        
        for path, should_log in test_cases:
            request = self.factory.get(path)
            self.assertEqual(
                self.middleware._should_log_request(request),
                should_log,
                f"Path {path} should{' not' if not should_log else ''} be logged"
            )

    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        import queue

        results = queue.Queue()
        request_count = 10

        def make_request():
            try:
                request = self.factory.get('/')
                response = self.middleware(request)
                results.put(response.status_code if response else 200)
            except Exception as e:
                results.put(e)

        # 创建并发请求
        threads = []
        for _ in range(request_count):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        # 等待所有请求完成
        for t in threads:
            t.join()

        # 检查结果
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())

        # 验证结果
        success_count = sum(1 for code in status_codes if code == 200)
        self.assertLessEqual(success_count, 5)  # 假设限制为5个请求

    def test_ip_blocking_with_attempts(self):
        """测试基于尝试次数的IP封禁"""
        # 配置自动封禁
        with override_settings(SECURITY_AUTO_BLOCK_CONFIG={
            'max_attempts': 3,
            'window': 300,  # 5分钟
            'block_duration': 3600  # 1小时
        }):
            # 模拟失败的登录尝试
            for _ in range(3):
                self.client.post('/login/', {
                    'username': 'wrong',
                    'password': 'wrong'
                })

            # 验证IP是否被自动封禁
            self.assertTrue(BlockedIP.objects.is_blocked('127.0.0.1'))
            blocked_ip = BlockedIP.objects.get(ip_address='127.0.0.1')
            self.assertEqual(blocked_ip.attempts_count, 3)

    def test_request_sanitization(self):
        """测试请求数据清理"""
        # 发送包含敏感数据的请求
        sensitive_data = {
            'username': 'test',
            'password': 'secret123',
            'credit_card': '1234-5678-9012-3456',
            'token': 'abc123'
        }

        self.client.post('/api/user/', sensitive_data)

        # 验证日志中的敏感数据处理
        log = AuditLog.objects.latest('created_at')
        self.assertNotIn('secret123', str(log.extra_data))
        self.assertNotIn('1234-5678-9012-3456', str(log.extra_data))
        self.assertNotIn('abc123', str(log.extra_data))

    def test_rate_limit_bypass_attempts(self):
        """测试绕过频率限制的尝试"""
        # 测试不同的IP伪装方式
        headers = [
            {'HTTP_X_FORWARDED_FOR': '10.0.0.1'},
            {'HTTP_X_REAL_IP': '10.0.0.2'},
            {'HTTP_CLIENT_IP': '10.0.0.3'},
            {'REMOTE_ADDR': '10.0.0.4'},
        ]

        with override_settings(SECURITY_RATE_LIMITS={'default': '1/m'}):
            for header in headers:
                # 每个"IP"都应该单独计数
                response = self.client.get('/', **header)
                self.assertNotEqual(response.status_code, 403)

                # 第二次请求应该被限制
                response = self.client.get('/', **header)
                self.assertEqual(response.status_code, 403)

    def test_dynamic_rate_limiting(self):
        """测试动态频率限制"""
        # 匿名用户请求
        for i in range(3):
            request = self.factory.get('/')
            request.user = None
            response = self.middleware(request)
            if i < 2:
                self.assertIsNone(response)
            else:
                self.assertEqual(response.status_code, 403)

        # 认证用户请求（应该有更高的限制）
        request = self.factory.get('/')
        request.user = self.user
        response = self.middleware(request)
        self.assertIsNone(response)

    def test_security_headers(self):
        """测试安全响应头"""
        request = self.factory.get('/')
        middleware = SecurityMiddleware(lambda r: type('Response', (), {
            'status_code': 200,
            'headers': {}
        }))
        
        response = middleware(request)
        
        # 验证安全头部
        expected_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'"
        }
        
        for header, value in expected_headers.items():
            self.assertEqual(response.headers.get(header), value)

    def test_maintenance_mode(self):
        """测试维护模式"""
        with override_settings(MAINTENANCE_MODE=True):
            # 普通用户应该看到维护页面
            response = self.client.get('/')
            self.assertEqual(response.status_code, 503)

            # 管理员应该可以正常访问
            self.client.login(username='testuser', password='testpass123')
            self.user.is_staff = True
            self.user.save()
            response = self.client.get('/')
            self.assertNotEqual(response.status_code, 503)

    def test_request_size_limits(self):
        """测试请求大小限制"""
        # 创建大文件
        large_data = 'x' * (10 * 1024 * 1024)  # 10MB
        
        # POST请求应该被拒绝
        response = self.client.post('/api/upload/', {'data': large_data})
        self.assertEqual(response.status_code, 413)  # Request Entity Too Large

    def test_cleanup_expired_blocks(self):
        """测试过期封禁清理"""
        # 创建一些过期的封禁记录
        BlockedIP.objects.create(
            ip_address='192.168.1.1',
            reason='Test blocking',
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        BlockedIP.objects.create(
            ip_address='192.168.1.2',
            reason='Test blocking',
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )

        # 运行清理
        from django.core.management import call_command
        call_command('cleanup_expired_blocks')

        # 验证结果
        self.assertEqual(BlockedIP.objects.count(), 1)
        self.assertTrue(BlockedIP.objects.filter(ip_address='192.168.1.2').exists())

    def test_auto_ip_blocking(self):
        """测试自动IP封禁"""
        # 模拟多次失败请求
        for _ in range(3):
            request = self.factory.post('/login/', {
                'username': 'wrong',
                'password': 'wrong'
            })
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            self.middleware(request)

        # 验证IP是否被自动封禁
        self.assertTrue(BlockedIP.objects.is_blocked('192.168.1.1'))
        blocked_ip = BlockedIP.objects.get(ip_address='192.168.1.1')
        self.assertEqual(blocked_ip.attempts_count, 3)

    def test_sensitive_data_handling(self):
        """测试敏感数据处理"""
        # 创建包含敏感数据的请求
        sensitive_data = {
            'username': 'test',
            'password': 'secret123',
            'credit_card': '1234-5678-9012-3456',
            'token': 'abc123'
        }
        request = self.factory.post('/api/user/', sensitive_data)
        request.META['CONTENT_TYPE'] = 'application/json'
        request._body = json.dumps(sensitive_data).encode('utf-8')

        # 处理请求
        self.middleware(request)

        # 验证日志中的敏感数据处理
        log = AuditLog.objects.latest('created_at')
        log_data = json.dumps(log.extra_data)
        self.assertNotIn('secret123', log_data)
        self.assertNotIn('1234-5678-9012-3456', log_data)
        self.assertNotIn('abc123', log_data)
        self.assertIn('***', log_data)

    def test_request_validation(self):
        """测试请求验证"""
        test_cases = [
            # 测试异常长的URL
            ('/' + 'a' * 2000, 414),  # URI Too Long
            # 测试异常的User-Agent
            ('/', 403, {'HTTP_USER_AGENT': 'Bad-Bot/1.0'}),
            # 测试无效的Content-Type
            ('/', 415, {'CONTENT_TYPE': 'invalid/type'}),
        ]

        for path, expected_status, headers in test_cases:
            request = self.factory.get(path, **headers)
            response = self.middleware(request)
            if response:
                self.assertEqual(response.status_code, expected_status)

    def test_error_handling(self):
        """测试错误处理"""
        def raise_error(request):
            raise ValueError("Test error")

        middleware = SecurityMiddleware(raise_error)
        request = self.factory.get('/')
        
        # 测试异常处理
        response = middleware(request)
        self.assertEqual(response.status_code, 500)
        
        # 验证错误日志
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action_type, 'error')
        self.assertEqual(log.severity, 'error')
        self.assertIn('Test error', log.action_detail)

    def test_rate_limit_reset(self):
        """测试频率限制重置"""
        from freezegun import freeze_time
        from datetime import datetime, timedelta

        with freeze_time("2024-01-01 12:00:00"):
            # 达到限制
            for _ in range(5):
                request = self.factory.get('/')
                self.middleware(request)

            # 验证被限制
            request = self.factory.get('/')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 403)

        # 时间前进一小时
        with freeze_time("2024-01-01 13:00:00"):
            # 验证限制已重置
            request = self.factory.get('/')
            response = self.middleware(request)
            self.assertIsNone(response)

    def tearDown(self):
        cache.clear() 