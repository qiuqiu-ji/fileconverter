"""批量操作处理"""
from django.conf import settings
from celery import shared_task
import os
import zipfile
import tempfile
import logging

logger = logging.getLogger(__name__)

@shared_task
def create_batch_download(task_ids, user_id):
    """创建批量下载包"""
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'download.zip')
            
            # 创建ZIP文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for task_id in task_ids:
                    task = ConversionTask.objects.get(id=task_id)
                    if task.output_file:
                        zf.write(
                            task.output_file.path,
                            os.path.basename(task.output_file.name)
                        )
            
            # 保存结果
            with open(zip_path, 'rb') as f:
                # 保存到临时存储
                key = f'batch_download:{user_id}:{uuid.uuid4()}'
                cache.set(key, f.read(), timeout=3600)
                return key
                
    except Exception as e:
        logger.error(f"Batch download creation failed: {str(e)}")
        raise 