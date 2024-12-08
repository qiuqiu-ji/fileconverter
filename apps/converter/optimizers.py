"""文件优化器集合"""
from PIL import Image
import os
from pdf2image import convert_from_path
import img2pdf
import PyPDF2
from io import BytesIO

class FileOptimizer:
    """文件优化基类"""
    def optimize(self, file_path, output_path=None):
        """执行优化"""
        raise NotImplementedError

class ImageOptimizer(FileOptimizer):
    """图片优化器"""
    def __init__(self):
        self.quality_settings = {
            'high': {'quality': 95, 'optimize': True},
            'medium': {'quality': 85, 'optimize': True},
            'low': {'quality': 75, 'optimize': True}
        }

    def optimize(self, file_path, output_path=None, quality='medium'):
        """优化图片"""
        if output_path is None:
            output_path = file_path

        with Image.open(file_path) as img:
            # 转换为RGB模式（如果是RGBA）
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            # 应用优化设置
            settings = self.quality_settings[quality]
            img.save(output_path, 
                    quality=settings['quality'], 
                    optimize=settings['optimize'])

    def resize_image(self, file_path, output_path, max_size):
        """调整图片大小"""
        with Image.open(file_path) as img:
            # 计算新尺寸
            ratio = min(max_size[0]/img.size[0], max_size[1]/img.size[1])
            if ratio < 1:
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            img.save(output_path, quality=95, optimize=True)

class PDFOptimizer(FileOptimizer):
    """PDF优化器"""
    def optimize(self, file_path, output_path=None, quality='medium'):
        """优化PDF文件"""
        if output_path is None:
            output_path = file_path

        # 根据质量级别设置DPI
        dpi_settings = {
            'high': 300,
            'medium': 200,
            'low': 150
        }
        dpi = dpi_settings[quality]

        # 将PDF转换为图片
        images = convert_from_path(file_path, dpi=dpi)
        
        # 创建临时图片文件
        image_files = []
        for i, image in enumerate(images):
            img_path = f'temp_{i}.jpg'
            image.save(img_path, 'JPEG', quality=85, optimize=True)
            image_files.append(img_path)

        # 将图片转回PDF
        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(image_files))

        # 清理临时文件
        for img_path in image_files:
            os.remove(img_path)

    def merge_pdfs(self, file_paths, output_path):
        """合并多个PDF文件"""
        merger = PyPDF2.PdfMerger()
        
        for path in file_paths:
            merger.append(path)
            
        merger.write(output_path)
        merger.close()

    def split_pdf(self, file_path, output_dir):
        """拆分PDF文件"""
        reader = PyPDF2.PdfReader(file_path)
        
        for i in range(len(reader.pages)):
            writer = PyPDF2.PdfWriter()
            writer.add_page(reader.pages[i])
            
            output_path = os.path.join(
                output_dir, 
                f'page_{i+1}.pdf'
            )
            
            with open(output_path, 'wb') as f:
                writer.write(f)

class DocumentOptimizer(FileOptimizer):
    """文档优化器"""
    def optimize(self, file_path, output_path=None):
        """优化文档文件"""
        # 根据文件类型调用不同的优化方法
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            optimizer = PDFOptimizer()
            optimizer.optimize(file_path, output_path)
        elif ext in ['.jpg', '.jpeg', '.png']:
            optimizer = ImageOptimizer()
            optimizer.optimize(file_path, output_path)

class OptimizerFactory:
    """优化器工厂"""
    def __init__(self):
        self.optimizers = {
            'image': ImageOptimizer(),
            'pdf': PDFOptimizer(),
            'document': DocumentOptimizer()
        }

    def get_optimizer(self, file_type):
        """获取优化器"""
        optimizer = self.optimizers.get(file_type)
        if optimizer is None:
            raise ValueError(f'不支持的文件类型：{file_type}')
        return optimizer

    def optimize_file(self, file_path, file_type, output_path=None, quality='medium'):
        """优化文件"""
        optimizer = self.get_optimizer(file_type)
        optimizer.optimize(file_path, output_path, quality) 