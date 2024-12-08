from rest_framework import serializers
from .models import ConversionTask, ConversionHistory, UploadSession

class ConversionTaskSerializer(serializers.ModelSerializer):
    """转换任务序列化器"""
    download_url = serializers.URLField(source='converted_file.url', read_only=True)
    
    class Meta:
        model = ConversionTask
        fields = [
            'id', 'status', 'original_format', 'target_format',
            'created_at', 'updated_at', 'processing_time',
            'file_size', 'error_message', 'download_url'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'updated_at',
            'processing_time', 'error_message', 'download_url'
        ]

class ConversionRequestSerializer(serializers.Serializer):
    """转换请求序列化器"""
    file = serializers.FileField()
    original_format = serializers.CharField(max_length=10)
    target_format = serializers.CharField(max_length=10)

    def validate(self, data):
        """验证转换格式"""
        from django.conf import settings
        
        original_format = data['original_format'].lower()
        target_format = data['target_format'].lower()
        
        if original_format not in settings.ALLOWED_FILE_TYPES:
            raise serializers.ValidationError(f"Unsupported input format: {original_format}")
            
        if target_format not in settings.ALLOWED_FILE_TYPES:
            raise serializers.ValidationError(f"Unsupported output format: {target_format}")
            
        return data

class BatchConversionSerializer(serializers.Serializer):
    """批量转换序列化器"""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        max_length=20  # 最多20个文件
    )
    target_format = serializers.CharField(max_length=10)

    def validate_target_format(self, value):
        """验证目标格式"""
        from django.conf import settings
        
        if value.lower() not in settings.ALLOWED_FILE_TYPES:
            raise serializers.ValidationError(f"Unsupported format: {value}")
        return value.lower()

class UploadSessionSerializer(serializers.ModelSerializer):
    """上传会话序列化器"""
    class Meta:
        model = UploadSession
        fields = [
            'id', 'session_id', 'filename', 'file_size',
            'chunk_size', 'total_chunks', 'uploaded_chunks',
            'created_at', 'expires_at', 'completed', 'progress'
        ]
        read_only_fields = [
            'id', 'session_id', 'created_at',
            'expires_at', 'completed', 'progress'
        ]

"""API序列化器"""
from rest_framework import serializers
from .models import ConversionTask

class ConversionTaskSerializer(serializers.ModelSerializer):
    """转换任务序列化器"""
    class Meta:
        model = ConversionTask
        fields = [
            'id', 'original_file', 'output_file',
            'target_format', 'status', 'progress',
            'error_message', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'status', 'progress', 'error_message',
            'created_at', 'completed_at'
        ]

class TaskCreateSerializer(serializers.ModelSerializer):
    """任务创建序列化器"""
    file = serializers.FileField(write_only=True)
    
    class Meta:
        model = ConversionTask
        fields = ['file', 'target_format']
    
    def create(self, validated_data):
        """创建任务"""
        file_obj = validated_data.pop('file')
        task = ConversionTask.objects.create(
            original_file=file_obj,
            **validated_data
        )
        return task

class TaskStatusSerializer(serializers.ModelSerializer):
    """任务状态序列化器"""
    class Meta:
        model = ConversionTask
        fields = ['id', 'status', 'progress', 'error_message']