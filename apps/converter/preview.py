"""文件预览处理器"""
from django.conf import settings
from django.core.exceptions import ValidationError
import os
import logging
from PIL import Image
import fitz  # PyMuPDF
import tempfile
from .utils import get_file_type

logger = logging.getLogger(__name__)

class PreviewGenerator:
    def __init__(self):
        self.settings = settings.CONVERSION_SETTINGS['preview']
        self.max_size = self.settings['max_size']
        self.timeout = self.settings['timeout']
        
    def generate_preview(self, file_path, format_type=None):
        """生成预览"""
        try:
            # 检查文件大小
            if os.path.getsize(file_path) > self.max_size:
                raise ValidationError("File too large for preview")
                
            # 根据文件类型生成预览
            file_type = format_type or get_file_type(file_path)
            
            if file_type in ['pdf', 'docx']:
                return self._generate_document_preview(file_path)
            elif file_type in ['jpg', 'png', 'gif']:
                return self._generate_image_preview(file_path)
            else:
                raise ValidationError(f"Unsupported preview format: {file_type}")
                
        except Exception as e:
            logger.error(f"Preview generation failed: {str(e)}")
            raise

    def _generate_document_preview(self, file_path):
        """生成文档预览"""
        try:
            with fitz.open(file_path) as doc:
                page = doc[0]  # 获取第一页
                # 设置合适的分辨率
                zoom = 2  # 放大2倍以获得更好的质量
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    pix.save(tmp.name)
                    return tmp.name
                
        except Exception as e:
            logger.error(f"Document preview generation failed: {str(e)}")
            raise

    def _generate_image_preview(self, file_path):
        """生成图片预览"""
        try:
            with Image.open(file_path) as img:
                # 计算预览尺寸
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
                
                # 保存预览
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name, 'PNG', optimize=True)
                    return tmp.name
                
        except Exception as e:
            logger.error(f"Image preview generation failed: {str(e)}")
            raise
</```
rewritten_file>