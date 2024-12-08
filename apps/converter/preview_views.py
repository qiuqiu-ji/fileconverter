from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .preview import PreviewFactory
import os
import mimetypes

preview_factory = PreviewFactory()

@login_required
@require_http_methods(["POST"])
def generate_preview(request):
    """生成文件预览"""
    try:
        file = request.FILES['file']
        
        # 保存上传的文件
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        # 生成预览
        preview_paths = preview_factory.generate_preview(temp_path)
        
        # 如果是单个预览文件，转换为列表
        if isinstance(preview_paths, str):
            preview_paths = [preview_paths]
            
        # 构建预览URL
        preview_urls = []
        for path in preview_paths:
            filename = os.path.basename(path)
            preview_url = request.build_absolute_uri(
                settings.MEDIA_URL + 'previews/' + filename
            )
            preview_urls.append(preview_url)
            
            # 移动预览文件到可访问目录
            preview_dir = os.path.join(settings.MEDIA_ROOT, 'previews')
            os.makedirs(preview_dir, exist_ok=True)
            os.rename(path, os.path.join(preview_dir, filename))
            
        return JsonResponse({
            'status': 'success',
            'previews': preview_urls
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

@login_required
@require_http_methods(["GET"])
def view_preview(request, filename):
    """查看预览文件"""
    preview_path = os.path.join(settings.MEDIA_ROOT, 'previews', filename)
    
    if not os.path.exists(preview_path):
        return JsonResponse({
            'status': 'error',
            'message': '预览文件不存在'
        }, status=404)
        
    # 获取文件类型
    content_type, _ = mimetypes.guess_type(filename)
    
    # 返回文件
    response = FileResponse(
        open(preview_path, 'rb'),
        content_type=content_type
    )
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response 