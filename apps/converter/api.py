"""转换API"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ConversionTask
from .serializers import (
    ConversionTaskSerializer,
    TaskCreateSerializer,
    TaskStatusSerializer
)

class ConversionTaskViewSet(viewsets.ModelViewSet):
    """
    文件转换任务API
    
    提供文件转换任务的创建、查询、管理等功能。
    
    list:
        获取当前用户的所有转换任务
        
    create:
        创建新的转换任务
        
    retrieve:
        获取指定任务的详细信息
        
    status:
        获取任务的当前状态
        
    retry:
        重试失败的任务
        
    download:
        下载转换后的文件
        
    batch_convert:
        批量创建转换任务
        
    batch_delete:
        批量删除任务
        
    statistics:
        获取任务统计数据
        
    usage:
        获取当前用户的使用情况
    """
    serializer_class = ConversionTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        return ConversionTask.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """获取序列化器类"""
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action == 'status':
            return TaskStatusSerializer
        return self.serializer_class
    
    def perform_create(self, serializer):
        """创建任务"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取任务状态"""
        task = self.get_object()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试任务"""
        task = self.get_object()
        if task.status != 'failed':
            return Response(
                {'error': '只能重试失败的任务'},
                status=400
            )
        
        task.retry()
        return Response({'message': '任务已重新加入队列'})
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载文件"""
        task = self.get_object()
        if not task.output_file:
            return Response(
                {'error': '文件不存在'},
                status=404
            )
        
        response = FileResponse(
            task.output_file,
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{task.get_output_filename()}"'
        return response 

    @action(detail=False, methods=['post'])
    def batch_convert(self, request):
        """批量转换"""
        serializer = BatchConversionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        files = serializer.validated_data['files']
        target_format = serializer.validated_data['target_format']
        
        # 检查用户配额
        if not self.request.user.can_batch_convert(len(files)):
            return Response({
                'error': '超出批量转换限制或配额不足'
            }, status=403)
        
        # 创建任务
        tasks = []
        for file in files:
            task = ConversionTask.objects.create(
                user=self.request.user,
                original_file=file,
                target_format=target_format
            )
            tasks.append(task)
        
        # 返回任务ID列表
        return Response({
            'task_ids': [task.id for task in tasks]
        })

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除"""
        task_ids = request.data.get('task_ids', [])
        if not task_ids:
            return Response({
                'error': '未指定任务ID'
            }, status=400)
        
        # 删除任务
        deleted = ConversionTask.objects.filter(
            id__in=task_ids,
            user=self.request.user
        ).delete()[0]
        
        return Response({
            'deleted_count': deleted
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取统计数据"""
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取时间范围
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # 查询任务
        tasks = self.get_queryset().filter(
            created_at__gte=start_date
        )
        
        # 计算统计数据
        stats = {
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='completed').count(),
            'failed_tasks': tasks.filter(status='failed').count(),
            'total_size': tasks.aggregate(Sum('file_size'))['file_size__sum'] or 0,
            
            # 按状态分组
            'status_distribution': dict(
                tasks.values('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            
            # 按格式分组
            'format_distribution': {
                'source': dict(
                    tasks.values('original_format')
                    .annotate(count=Count('id'))
                    .values_list('original_format', 'count')
                ),
                'target': dict(
                    tasks.values('target_format')
                    .annotate(count=Count('id'))
                    .values_list('target_format', 'count')
                )
            },
            
            # 每日统计
            'daily_stats': list(
                tasks.extra(
                    select={'date': 'DATE(created_at)'}
                ).values('date')
                .annotate(
                    count=Count('id'),
                    completed=Count('id', filter=models.Q(status='completed')),
                    failed=Count('id', filter=models.Q(status='failed')),
                    size=Sum('file_size')
                ).order_by('date')
            )
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def usage(self, request):
        """获取使用情况"""
        user = request.user
        
        usage_data = {
            'quota': {
                'used': user.used_quota,
                'total': user.quota_plan_limit,
                'remaining': user.get_remaining_quota()
            },
            'storage': {
                'used': user.get_storage_usage(),
                'total': user.storage_quota,
                'remaining': user.get_remaining_storage()
            },
            'features': {
                'can_batch_convert': user.can_batch_convert(),
                'can_use_priority': user.can_use_priority_queue(),
                'supported_formats': user.get_supported_formats()
            },
            'limits': {
                'max_file_size': user.get_max_file_size(),
                'max_batch_size': user.get_max_batch_size(),
                'concurrent_tasks': user.get_concurrent_task_limit()
            }
        }
        
        return Response(usage_data) 