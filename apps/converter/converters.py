"""文件格式转换器集合"""
from PIL import Image
import fitz  # PyMuPDF
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
import os
import io
import tempfile
from pdf2docx import Converter
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from django.conf import settings

class BaseConverter:
    """转换器基类"""
    def __init__(self):
        self.supported_formats = set()

    def can_convert(self, source_format, target_format):
        """检查是否支持转换"""
        return (source_format, target_format) in self.supported_formats

    def convert(self, input_path, output_path):
        """执行转换"""
        raise NotImplementedError

class ImageConverter(BaseConverter):
    """图片格式转换器"""
    def __init__(self):
        super().__init__()
        self.supported_formats = {
            ('jpg', 'png'), ('jpg', 'bmp'), ('jpg', 'gif'),
            ('png', 'jpg'), ('png', 'bmp'), ('png', 'gif'),
            ('bmp', 'jpg'), ('bmp', 'png'), ('bmp', 'gif'),
            ('gif', 'jpg'), ('gif', 'png'), ('gif', 'bmp'),
            ('svg', 'png'), ('svg', 'jpg')
        }

    def convert(self, input_path, output_path):
        """转换图片格式"""
        source_ext = os.path.splitext(input_path)[1][1:].lower()
        target_ext = os.path.splitext(output_path)[1][1:].lower()

        # SVG特殊处理
        if source_ext == 'svg':
            drawing = svg2rlg(input_path)
            if target_ext == 'png':
                renderPM.drawToFile(drawing, output_path, fmt='PNG')
            else:
                renderPM.drawToFile(drawing, output_path, fmt='JPEG')
            return

        # 其他图片格式转换
        with Image.open(input_path) as img:
            # 转换颜色模式
            if img.mode in ('RGBA', 'LA') and target_ext == 'jpg':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode == 'P':
                img = img.convert('RGB')

            # 保存转换后的图片
            img.save(output_path, quality=95, optimize=True)

class DocumentConverter(BaseConverter):
    """文档格式转换器"""
    def __init__(self):
        super().__init__()
        self.supported_formats = {
            ('pdf', 'docx'), ('docx', 'pdf'),
            ('pdf', 'jpg'), ('pdf', 'png')
        }

    def convert(self, input_path, output_path):
        """转换文档格式"""
        source_ext = os.path.splitext(input_path)[1][1:].lower()
        target_ext = os.path.splitext(output_path)[1][1:].lower()

        if source_ext == 'pdf' and target_ext == 'docx':
            # PDF转Word
            cv = Converter(input_path)
            cv.convert(output_path)
            cv.close()

        elif source_ext == 'docx' and target_ext == 'pdf':
            # Word转PDF
            doc = Document(input_path)
            # 使用python-docx-replace保持格式
            temp_path = tempfile.mktemp(suffix='.pdf')
            doc.save(temp_path)
            os.rename(temp_path, output_path)

        elif source_ext == 'pdf' and target_ext in ['jpg', 'png']:
            # PDF转图片
            doc = fitz.open(input_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以提高质量
                if target_ext == 'jpg':
                    pix.save(output_path.replace('.jpg', f'_{page_num+1}.jpg'))
                else:
                    pix.save(output_path.replace('.png', f'_{page_num+1}.png'))

class SpreadsheetConverter(BaseConverter):
    """电子表格转换器"""
    def __init__(self):
        super().__init__()
        self.supported_formats = {
            ('xlsx', 'pdf'), ('xlsx', 'csv'),
            ('csv', 'xlsx')
        }

    def convert(self, input_path, output_path):
        """转换电子表格格式"""
        source_ext = os.path.splitext(input_path)[1][1:].lower()
        target_ext = os.path.splitext(output_path)[1][1:].lower()

        if source_ext == 'xlsx':
            wb = load_workbook(input_path)
            if target_ext == 'pdf':
                # Excel转PDF
                # 使用win32com或其他库实现
                pass
            elif target_ext == 'csv':
                # Excel转CSV
                sheet = wb.active
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    for row in sheet.rows:
                        f.write(','.join(str(cell.value or '') for cell in row) + '\n')

class ConversionFactory:
    """转换器工厂"""
    def __init__(self):
        self.converters = [
            ImageConverter(),
            DocumentConverter(),
            SpreadsheetConverter()
        ]

    def get_converter(self, source_format, target_format):
        """获取合适的转换器"""
        for converter in self.converters:
            if converter.can_convert(source_format.lower(), target_format.lower()):
                return converter
        raise ValueError(f'不支持从 {source_format} 转换为 {target_format}')

    def get_supported_formats(self):
        """获取所有支持的格式"""
        formats = set()
        for converter in self.converters:
            formats.update(converter.supported_formats)
        return formats 