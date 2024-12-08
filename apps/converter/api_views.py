from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext as _

from .models import ConversionTask
from .serializers import (
    ConversionTaskSerializer,
    ConversionRequestSerializer,
    BatchConversionSerializer
)
from .tasks import convert_file_task
from apps.security.validators import FileValidator, SecurityScanner

class ConversionViewSet(viewsets.ModelViewSet):
    """文件转换API视图集"""
    serializer_class = ConversionTaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取当前用户的转换任务"""
        return ConversionTask.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def convert(self, request):
        """单文件转换"""
        serializer = ConversionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # 验证文件
            file = request.FILES['file']
            FileValidator.validate_file(file)
            SecurityScanner.scan_file(file)
            
            # 创建转换任务
            task = ConversionTask.objects.create(
                user=request.user,
                original_file=file,
                original_format=serializer.validated_data['original_format'],
                target_format=serializer.validated_data['target_format'],
                file_size=file.size
            )
            
            # 启动异步转换
            convert_file_task.delay(task.id)
            
            return Response({
                'task_id': task.id,
                'status': 'accepted'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def batch(self, request):
        """批量转换"""
        serializer = BatchConversionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            tasks = []
            for file in request.FILES.getlist('files'):
                # 验证每个文件
                FileValidator.validate_file(file)
                SecurityScanner.scan_file(file)
                
                # ��建转换任务
                task = ConversionTask.objects.create(
                    user=request.user,
                    original_file=file,
                    original_format=serializer.validated_data['original_format'],
                    target_format=serializer.validated_data['target_format'],
                    file_size=file.size
                )
                tasks.append(task)
                
                # 启动异步转换
                convert_file_task.delay(task.id)
            
            return Response({
                'task_ids': [task.id for task in tasks],
                'status': 'accepted'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取任务状态"""
        task = self.get_object()
        serializer = self.get_serializer(task)
        return Response(serializer.data) 