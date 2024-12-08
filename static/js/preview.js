/**
 * 文件预览组件
 */
class FilePreview {
    constructor() {
        this.previewContainer = document.createElement('div');
        this.previewContainer.className = 'preview-container';
        document.body.appendChild(this.previewContainer);
    }

    /**
     * 显示文件预览
     * @param {File} file - 要预览的文件
     */
    async showPreview(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        let previewContent = '';

        try {
            switch (true) {
                case ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension):
                    previewContent = await this.createImagePreview(file);
                    break;
                case extension === 'svg':
                    previewContent = await this.createSvgPreview(file);
                    break;
                case extension === 'pdf':
                    previewContent = await this.createPdfPreview(file);
                    break;
                case ['docx', 'xlsx', 'pptx'].includes(extension):
                    previewContent = await this.createOfficePreview(file);
                    break;
                default:
                    throw new Error('不支持预览此文件格式');
            }

            this.showPreviewDialog(previewContent);
        } catch (error) {
            console.error('预览失败:', error);
            this.showError(error.message);
        }
    }

    /**
     * 创建图片预览
     */
    createImagePreview(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                resolve(`
                    <div class="image-preview">
                        <img src="${e.target.result}" alt="${file.name}">
                    </div>
                `);
            };
            reader.onerror = () => reject(new Error('图片加载失败'));
            reader.readAsDataURL(file);
        });
    }

    /**
     * 创建SVG预览
     */
    createSvgPreview(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                resolve(`
                    <div class="svg-preview">
                        ${e.target.result}
                    </div>
                `);
            };
            reader.onerror = () => reject(new Error('SVG加载失败'));
            reader.readAsText(file);
        });
    }

    /**
     * 创建PDF预览
     */
    createPdfPreview(file) {
        return new Promise((resolve, reject) => {
            const fileUrl = URL.createObjectURL(file);
            resolve(`
                <div class="pdf-preview">
                    <iframe src="${fileUrl}#toolbar=0" type="application/pdf"></iframe>
                </div>
            `);
            // 在预览关闭时释放URL
            this.onClose = () => URL.revokeObjectURL(fileUrl);
        });
    }

    /**
     * 创建Office文档预览
     */
    async createOfficePreview(file) {
        try {
            // 上传文件到服务器进行预览转换
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/preview/office/', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('预览生成失败');
            }

            const data = await response.json();
            return `
                <div class="office-preview">
                    <iframe src="${data.preview_url}" frameborder="0"></iframe>
                </div>
            `;
        } catch (error) {
            throw new Error('Office文档预览失败');
        }
    }

    /**
     * 显示预览对话框
     */
    showPreviewDialog(content) {
        this.previewContainer.innerHTML = `
            <div class="preview-dialog">
                <div class="preview-header">
                    <h3>文件预览</h3>
                    <button class="close-preview" onclick="filePreview.closePreview()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="preview-content">
                    ${content}
                </div>
            </div>
        `;
        this.previewContainer.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    /**
     * 关闭预览
     */
    closePreview() {
        if (this.onClose) {
            this.onClose();
            this.onClose = null;
        }
        this.previewContainer.style.display = 'none';
        document.body.style.overflow = '';
    }

    /**
     * 显示错误信息
     */
    showError(message) {
        this.previewContainer.innerHTML = `
            <div class="preview-error">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
                <button onclick="filePreview.closePreview()">关闭</button>
            </div>
        `;
        this.previewContainer.style.display = 'flex';
    }
}

// 创建全局预览实例
window.filePreview = new FilePreview(); 