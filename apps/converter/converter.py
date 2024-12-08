"""文件转换器"""
from django.conf import settings
import os
import logging
from PIL import Image
from .validators import validate_conversion_options

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self):
        self.settings = settings.CONVERSION_SETTINGS
        self.chunk_size = self.settings['chunk_size']
        
    def convert(self, input_path, output_format, options=None):
        """执行转换"""
        try:
            # 验证选项
            options = validate_conversion_options(
                input_path,
                output_format,
                options
            )
            
            # 根据格式选择转换器
            if output_format in ['jpg', 'png']:
                return self._convert_image(input_path, output_format, options)
            elif output_format == 'pdf':
                return self._convert_to_pdf(input_path, options)
            else:
                raise ValueError(f"Unsupported format: {output_format}")
                
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise 

    def _convert_image(self, input_path, output_format, options):
        """转换图片"""
        try:
            with Image.open(input_path) as img:
                # 应用质量选项
                if options.get('quality') == 'high':
                    dpi = options.get('dpi', 300)
                    img.info['dpi'] = (dpi, dpi)
                    
                # 调整大小
                if 'resize' in options:
                    width = options['resize'].get('width')
                    height = options['resize'].get('height')
                    if width and height:
                        img = img.resize((width, height), Image.LANCZOS)
                
                # 保存转换后的图片
                output_path = self._get_output_path(input_path, output_format)
                img.save(
                    output_path,
                    format=output_format.upper(),
                    quality=options.get('jpeg_quality', 95),
                    optimize=True
                )
                
                return output_path
                
        except Exception as e:
            logger.error(f"Image conversion failed: {str(e)}")
            raise
            
    def _convert_to_pdf(self, input_path, options):
        """转换为PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            output_path = self._get_output_path(input_path, 'pdf')
            
            # 创建PDF文档
            c = canvas.Canvas(output_path, pagesize=letter)
            
            # 根据输入文件类型处理
            input_format = os.path.splitext(input_path)[1][1:].lower()
            
            if input_format in ['jpg', 'png', 'gif']:
                # 图片转PDF
                img = Image.open(input_path)
                c.drawImage(input_path, 0, 0, *letter)
            elif input_format == 'txt':
                # 文本转PDF
                with open(input_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                c.drawString(72, 720, text)
            else:
                raise ValueError(f"Unsupported input format: {input_format}")
                
            c.save()
            return output_path
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise
            
    def _get_output_path(self, input_path, output_format):
        """获取输出文件路径"""
        filename = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(
            self.settings['temp_dir'],
            f"{filename}.{output_format}"
        )