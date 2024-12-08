from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from celery import shared_task
from django.views.generic import ListView, View
from django.db.models import Q, Sum
from django.contrib.auth.mixins import LoginRequiredMixin
import os

from .models import ConversionTask, ConversionHistory, UploadSession, PreviewTask
from .tasks import convert_file_task
from apps.security.validators import FileValidator, SecurityScanner
from apps.security.decorators import check_conversion_limits
from .error_handlers import handle_conversion_errors, FileValidationError, ConversionProcessError

@login_required
@check_conversion_limits
def upload_file(request):
    """处理文件上传"""
    if request.method == 'POST':
        try:
            file = request.FILES['file']
            target_format = request.POST.get('target_format')
            
            # 验证文件
            try:
                FileValidator.validate_file(file)
                SecurityScanner.scan_file(file)
                SecurityScanner.check_filename(file.name)
            except ValidationError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            
            # 创建转换任务
            task = ConversionTask.objects.create(
                user=request.user,
                original_file=file,
                original_format=os.path.splitext(file.name)[1][1:].lower(),
                target_format=target_format,
                file_size=file.size
            )

            # 记录转换历史
            ConversionHistory.objects.create(
                user=request.user,
                task=task,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            # 启动异步转换任务
            convert_file_task.delay(task.id)

            return JsonResponse({
                'status': 'success',
                'task_id': task.id
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': _('Method not allowed')
    }, status=405)

@login_required
def check_status(request, task_id):
    """检查转换任务状态"""
    try:
        task = ConversionTask.objects.get(id=task_id, user=request.user)
        data = {
            'status': task.status,
            'created_at': task.created_at,
            'updated_at': task.updated_at
        }

        if task.status == 'completed':
            data['download_url'] = task.converted_file.url
        elif task.status == 'failed':
            data['error_message'] = task.error_message

        return JsonResponse(data)

    except ConversionTask.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('Task not found')
        }, status=404)

class ConversionHistoryView(LoginRequiredMixin, ListView):
    """转换历史视图"""
    model = ConversionTask
    template_name = 'converter/history.html'
    context_object_name = 'tasks'
    paginate_by = 20
    
    def get_queryset(self):
        """获取查询集"""
        queryset = ConversionTask.objects.filter(user=self.request.user)
        
        # 过滤条件
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # 日期范围
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__range=[start_date, end_date]
            )
            
        # 搜索
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(original_file__icontains=search) |
                Q(output_file__icontains=search)
            )
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 添加统计数据
        stats = {
            'total_tasks': self.get_queryset().count(),
            'completed_tasks': self.get_queryset().filter(status='completed').count(),
            'failed_tasks': self.get_queryset().filter(status='failed').count(),
            'total_size': self.get_queryset().aggregate(
                total_size=Sum('file_size')
            )['total_size'] or 0
        }
        context['stats'] = stats
        
        # 添加过滤选项
        context['status_choices'] = ConversionTask.STATUS_CHOICES
        
        return context

class HistoryAPIView(LoginRequiredMixin, View):
    """历史记录API"""
    
    def post(self, request):
        """批量操作"""
        action = request.POST.get('action')
        task_ids = request.POST.getlist('task_ids')
        
        if not task_ids:
            return JsonResponse({'error': '未选择任务'}, status=400)
            
        tasks = ConversionTask.objects.filter(
            id__in=task_ids,
            user=request.user
        )
        
        if action == 'delete':
            # 删除任务
            for task in tasks:
                task.delete_files()  # 删除���关文件
            tasks.delete()
            return JsonResponse({'message': '删除成功'})
            
        elif action == 'retry':
            # 重试失败的任务
            for task in tasks.filter(status='failed'):
                task.retry()
            return JsonResponse({'message': '重试任务已添加到队列'})
            
        elif action == 'download':
            # 批量下载
            if tasks.count() > 10:
                return JsonResponse({'error': '一次最多下载10个文件'}, status=400)
                
            zip_file = create_zip_archive(tasks)
            response = FileResponse(
                zip_file,
                content_type='application/zip'
            )
            response['Content-Disposition'] = 'attachment; filename="converted_files.zip"'
            return response
            
        return JsonResponse({'error': '无效的操作'}, status=400)

def create_zip_archive(tasks):
    """创建ZIP压缩包"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for task in tasks:
            if task.output_file:
                file_name = os.path.basename(task.output_file.name)
                zip_file.write(task.output_file.path, file_name)
                
    zip_buffer.seek(0)
    return zip_buffer

@handle_conversion_errors
def convert_file(request):
    """文件转换视图"""
    try:
        if 'file' not in request.FILES:
            raise FileValidationError(_('No file provided'))
            
        file = request.FILES['file']
        target_format = request.POST.get('target_format')
        
        if not target_format:
            raise FileValidationError(_('Target format not specified'))
        
        # 创建转换任务
        task = create_conversion_task(file, target_format, request.user)
        
        # 返回任务ID
        return JsonResponse({
            'status': 'success',
            'task_id': task.id
        })
        
    except ValidationError as e:
        raise FileValidationError(str(e))
    except Exception as e:
        raise ConversionProcessError(str(e))

@login_required
def download_file(request, task_id):
    """下载转换后的文件"""
    try:
        task = ConversionTask.objects.get(id=task_id, user=request.user)
        
        if task.status != 'completed':
            return JsonResponse({
                'status': 'error',
                'message': _('File not ready')
            }, status=400)
            
        if not task.converted_file:
            return JsonResponse({
                'status': 'error',
                'message': _('File not found')
            }, status=404)
            
        response = FileResponse(
            task.converted_file.open('rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{task.converted_file.name}"'
        return response
        
    except ConversionTask.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('Task not found')
        }, status=404)

def create_upload_session(request):
    """创建上传会话"""
    # 检查每日转换限制
    today = timezone.now().date()
    daily_count = ConversionTask.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    
    if daily_count >= request.user.daily_conversion_limit:
        return JsonResponse({
            'error': 'Daily conversion limit exceeded'
        }, status=429)
    
    # 检查存储配额
    filesize = int(request.POST.get('filesize', 0))
    current_usage = request.user.get_storage_usage()
    
    if current_usage + filesize > request.user.storage_quota:
        return JsonResponse({
            'error': 'Storage quota exceeded'
        }, status=400)
    
    # 检查并发上传限制
    active_sessions = UploadSession.objects.filter(
        user=request.user,
        status='active'
    ).count()
    
    if active_sessions >= 5:  # 最大并发数
        return JsonResponse({
            'error': 'Too many concurrent uploads'
        }, status=429)
    
    # 创建上传会话
    session = UploadSession.objects.create(
        user=request.user,
        filename=request.POST.get('filename'),
        filesize=filesize,
        target_format=request.POST.get('target_format')
    )
    
    return JsonResponse({
        'session_id': session.id
    }) 

@shared_task
def generate_preview(task_id):
    """生成预览文件"""
    preview_task = PreviewTask.objects.get(id=task_id)
    conversion_task = preview_task.conversion_task
    
    try:
        # 根据文件类型生成预览
        if conversion_task.target_format == 'pdf':
            preview_file = generate_pdf_preview(conversion_task.converted_file)
        elif conversion_task.target_format in ['jpg', 'png']:
            preview_file = generate_image_preview(conversion_task.converted_file)
        else:
            raise ValueError('Unsupported preview format')
            
        preview_task.preview_file = preview_file
        preview_task.status = 'completed'
        preview_task.save()
        
    except Exception as e:
        preview_task.status = 'failed'
        preview_task.save()
        raise

def preview_file(request, task_id):
    """文件预览处理"""
    try:
        task = ConversionTask.objects.get(id=task_id, user=request.user)
    except ConversionTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
        
    if task.status != 'completed':
        return JsonResponse({'error': 'Task not ready'}, status=400)
    
    # 检查是否需要异步生成预览
    if request.method == 'POST' or is_large_file(task.converted_file):
        preview_task = PreviewTask.objects.create(
            conversion_task=task,
            status='pending'
        )
        generate_preview.delay(preview_task.id)
        return JsonResponse({
            'preview_id': preview_task.id
        }, status=202)
    
    # 直接返回预览
    return serve_preview(task.converted_file) 

# 添加辅助函数
def is_large_file(file):
    """检查是否是大文件（超过10MB）"""
    return file.size > 10 * 1024 * 1024

def generate_pdf_preview(file):
    """生成PDF预览"""
    from pdf2image import convert_from_path
    import tempfile
    import os
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 转换第一页为图片
        images = convert_from_path(file.path, first_page=1, last_page=1)
        if images:
            preview_path = os.path.join(temp_dir, 'preview.jpg')
            images[0].save(preview_path, 'JPEG')
            
            # 返回预览文件
            with open(preview_path, 'rb') as f:
                from django.core.files import File
                return File(f)
    return None

def generate_image_preview(file):
    """生成图片预览"""
    from PIL import Image
    import tempfile
    import os
    
    # 创建缩略图
    with Image.open(file.path) as img:
        # 设置最大尺寸
        max_size = (800, 800)
        img.thumbnail(max_size)
        
        # 保存预览
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            img.save(temp_file, 'JPEG')
            
            # 返回预览文件
            from django.core.files import File
            return File(open(temp_file.name, 'rb'))

def serve_preview(file):
    """提供文件预览"""
    from django.http import FileResponse
    import mimetypes
    
    content_type = mimetypes.guess_type(file.name)[0]
    response = FileResponse(file.open('rb'), content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{file.name}"'
    return response

@login_required
def preview_status(request, preview_id):
    """检查预览生成状态"""
    try:
        preview = PreviewTask.objects.get(id=preview_id)
        
        data = {
            'status': preview.status,
            'created_at': preview.created_at,
            'updated_at': preview.updated_at
        }
        
        if preview.status == 'completed':
            data['preview_url'] = preview.preview_file.url
        
        return JsonResponse(data)
        
    except PreviewTask.DoesNotExist:
        return JsonResponse({
            'error': 'Preview task not found'
        }, status=404) 