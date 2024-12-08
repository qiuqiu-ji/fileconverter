from PIL import Image
from pdf2docx import Converter
from docx2pdf import convert
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

class FileConverter:
    """文件格式转换器"""
    
    @staticmethod
    def get_file_extension(filename):
        """获取文件扩展名"""
        return os.path.splitext(filename)[1].lower()[1:]

    @staticmethod
    def convert_image(input_path, output_path, target_format):
        """图片格式转换"""
        try:
            # SVG转换需要特殊处理
            if input_path.lower().endswith('.svg'):
                drawing = svg2rlg(input_path)
                renderPM.drawToFile(drawing, output_path, fmt=target_format.upper())
            else:
                image = Image.open(input_path)
                # 如果是PNG，需要移除透明通道
                if target_format.lower() == 'jpg' or target_format.lower() == 'jpeg':
                    if image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                image.save(output_path, target_format.upper())
            return True
        except Exception as e:
            raise Exception(f"图片转换失败: {str(e)}")

    @staticmethod
    def convert_pdf_to_docx(input_path, output_path):
        """PDF转Word"""
        try:
            cv = Converter(input_path)
            cv.convert(output_path)
            cv.close()
            return True
        except Exception as e:
            raise Exception(f"PDF转Word失败: {str(e)}")

    @staticmethod
    def convert_docx_to_pdf(input_path, output_path):
        """Word转PDF"""
        try:
            convert(input_path, output_path)
            return True
        except Exception as e:
            raise Exception(f"Word转PDF失败: {str(e)}")

    def convert_file(self, input_path, output_path, source_format, target_format):
        """统一的文件转换入口"""
        # 图片格式转换
        image_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']
        if source_format in image_formats and target_format in image_formats:
            return self.convert_image(input_path, output_path, target_format)
        
        # PDF和Word互转
        if source_format == 'pdf' and target_format == 'docx':
            return self.convert_pdf_to_docx(input_path, output_path)
        elif source_format == 'docx' and target_format == 'pdf':
            return self.convert_docx_to_pdf(input_path, output_path)
            
        raise Exception(f"不支持从 {source_format} 转换为 {target_format}") 