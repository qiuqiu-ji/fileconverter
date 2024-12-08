"""转换质量控制"""
from django.conf import settings
import os
import logging
from PIL import Image
import fitz

logger = logging.getLogger(__name__)

class QualityOptimizer:
    """质量优化器"""
    
    def __init__(self):
        self.settings = settings.CONVERSION_SETTINGS['quality']
        
    def optimize_image(self, image_path, options):
        """优化图片"""
        try:
            with Image.open(image_path) as img:
                # 设置DPI
                dpi = options.get('dpi', self.settings['default_dpi'])
                img.info['dpi'] = (dpi, dpi)
                
                # 调整大小
                if 'resize' in options:
                    width = options['resize'].get('width')
                    height = options['resize'].get('height')
                    if width and height:
                        img = img.resize((width, height), Image.LANCZOS)
                
                # 优化质量
                quality = options.get('quality', self.settings['default_quality'])
                optimize = options.get('optimize', True)
                
                # 保存优化后的图片
                img.save(
                    image_path,
                    quality=quality,
                    optimize=optimize,
                    dpi=(dpi, dpi)
                )
                
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            raise
            
    def optimize_pdf(self, pdf_path, options):
        """优化PDF"""
        try:
            doc = fitz.open(pdf_path)
            
            # 设置压缩选项
            doc.save(
                pdf_path,
                garbage=options.get('clean_metadata', True),
                deflate=options.get('compress', True),
                clean=options.get('clean_content', True)
            )
            
        except Exception as e:
            logger.error(f"PDF optimization failed: {str(e)}")
            raise