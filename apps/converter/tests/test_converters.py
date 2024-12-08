"""转换器测试"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import os
from ..converters import (
    ImageConverter,
    DocumentConverter,
    SpreadsheetConverter,
    ConversionFactory
)

class ImageConverterTests(TestCase):
    """图片转换器测试"""
    
    def setUp(self):
        self.converter = ImageConverter()
        self.test_files_dir = os.path.join(settings.BASE_DIR, 'tests', 'test_files')
        
    def test_jpg_to_png_conversion(self):
        """测试JPG转PNG"""
        input_path = os.path.join(self.test_files_dir, 'test.jpg')
        output_path = os.path.join(self.test_files_dir, 'output.png')
        
        self.converter.convert(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # 清理测试文件
        if os.path.exists(output_path):
            os.remove(output_path)
            
    def test_png_with_transparency(self):
        """测试带透明度的PNG转换"""
        input_path = os.path.join(self.test_files_dir, 'transparent.png')
        output_path = os.path.join(self.test_files_dir, 'output.jpg')
        
        self.converter.convert(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # 清理测试文件
        if os.path.exists(output_path):
            os.remove(output_path)

class DocumentConverterTests(TestCase):
    """文档转换器测试"""
    
    def setUp(self):
        self.converter = DocumentConverter()
        self.test_files_dir = os.path.join(settings.BASE_DIR, 'tests', 'test_files')
        
    def test_pdf_to_docx_conversion(self):
        """测试PDF转DOCX"""
        input_path = os.path.join(self.test_files_dir, 'test.pdf')
        output_path = os.path.join(self.test_files_dir, 'output.docx')
        
        self.converter.convert(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # 清理测试文件
        if os.path.exists(output_path):
            os.remove(output_path)
            
    def test_docx_to_pdf_conversion(self):
        """测试DOCX转PDF"""
        input_path = os.path.join(self.test_files_dir, 'test.docx')
        output_path = os.path.join(self.test_files_dir, 'output.pdf')
        
        self.converter.convert(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # 清理测试文件
        if os.path.exists(output_path):
            os.remove(output_path)

class ConversionFactoryTests(TestCase):
    """转换工厂测试"""
    
    def setUp(self):
        self.factory = ConversionFactory()
        
    def test_get_converter(self):
        """测试获取转换器"""
        # 图片转换器
        converter = self.factory.get_converter('jpg', 'png')
        self.assertIsInstance(converter, ImageConverter)
        
        # 文档转换器
        converter = self.factory.get_converter('pdf', 'docx')
        self.assertIsInstance(converter, DocumentConverter)
        
        # 电子表格转换器
        converter = self.factory.get_converter('xlsx', 'pdf')
        self.assertIsInstance(converter, SpreadsheetConverter)
        
    def test_unsupported_format(self):
        """测试不支持的格式"""
        with self.assertRaises(ValueError):
            self.factory.get_converter('xyz', 'abc') 