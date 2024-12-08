from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from .upload import UploadSessionManager
import json

upload_manager = UploadSessionManager()

@require_http_methods(["POST"])
def create_upload_session(request):
    """创建上传会话"""
    try:
        data = json.loads(request.body)
        session = upload_manager.create_session(
            filename=data['filename'],
            file_size=data['size'],
            total_chunks=data['totalChunks']
        )
        return JsonResponse({
            'uploadId': session['id'],
            'uploadedChunks': list(session['uploaded_chunks'])
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@require_http_methods(["POST"])
def upload_chunk(request):
    """上传文件分片"""
    try:
        chunk_file = request.FILES['chunk']
        chunk_index = int(request.POST['chunkIndex'])
        upload_id = request.POST['uploadId']
        
        session = upload_manager.save_chunk(upload_id, chunk_index, chunk_file)
        
        return JsonResponse({
            'uploaded': True,
            'chunkIndex': chunk_index,
            'uploadedChunks': list(session['uploaded_chunks'])
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

@require_http_methods(["POST"])
def complete_upload(request):
    """完成上传"""
    try:
        data = json.loads(request.body)
        file_path = upload_manager.merge_chunks(data['uploadId'])
        
        return JsonResponse({
            'status': 'success',
            'file_path': file_path
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=400) 