class FileUploader {
    constructor() {
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.uploadContainer = document.getElementById('uploadContainer');
        
        this.initializeEventListeners();
        
        // 添加批量上传相关属性
        this.files = new Map(); // 存储待转换的文件
        this.batchProgress = new Map(); // 存储每个文件的转换进度
        
        // 修改文件输入框为支持多选
        this.fileInput.setAttribute('multiple', 'true');
    }

    initializeEventListeners() {
        // 拖拽事件
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('drag-over');
        });

        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('drag-over');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelection(files[0]);
            }
        });

        // 文件选择事件
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelection(e.target.files[0]);
            }
        });
    }

    handleFileSelection(files) {
        // 处理多个文件
        Array.from(files).forEach(file => {
            // 验证文件
            if (this.validateFile(file)) {
                this.files.set(file.name, file);
                this.updateFileList();
            }
        });
    }

    validateFile(file) {
        // 文件大小检查
        if (file.size > 10 * 1024 * 1024) {
            this.showError(`文件 ${file.name} 大小超过10MB限制`);
            return false;
        }

        // 文件类型检查
        const extension = file.name.split('.').pop().toLowerCase();
        const allowedFormats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'pdf', 'docx', 'xlsx', 'pptx'];
        if (!allowedFormats.includes(extension)) {
            this.showError(`不支持的文件格式：${extension}`);
            return false;
        }

        return true;
    }

    updateFileList() {
        const fileListHtml = `
            <div class="selected-files">
                <h3>已选择的文件</h3>
                <div class="file-list">
                    ${Array.from(this.files.entries()).map(([name, file]) => `
                        <div class="file-item" data-filename="${name}">
                            <div class="file-info">
                                <i class="fas fa-file"></i>
                                <span class="filename">${name}</span>
                                <span class="filesize">(${this.formatFileSize(file.size)})</span>
                            </div>
                            <button class="remove-file" onclick="fileUploader.removeFile('${name}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
                <div class="batch-actions">
                    <button class="start-batch" onclick="fileUploader.startBatchConversion()">
                        开始转换 (${this.files.size}个文件)
                    </button>
                    <button class="clear-all" onclick="fileUploader.clearFiles()">
                        清空列表
                    </button>
                </div>
            </div>
        `;

        this.uploadContainer.innerHTML = fileListHtml;
    }

    removeFile(filename) {
        this.files.delete(filename);
        this.updateFileList();
    }

    clearFiles() {
        this.files.clear();
        this.updateFileList();
    }

    async startBatchConversion() {
        if (this.files.size === 0) {
            this.showError('请先选择要转换的文件');
            return;
        }

        // 显示批量转换进度界面
        this.showBatchProgress();

        // 并行处理所有文件
        const conversions = Array.from(this.files.values()).map(file => 
            this.convertFile(file)
        );

        try {
            await Promise.all(conversions);
            this.showBatchComplete();
        } catch (error) {
            this.showError('批量转换过程中出现错误');
        }
    }

    async convertFile(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('target_format', this.getTargetFormat(file));

            const response = await fetch('/api/convert/', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`转换失败: ${file.name}`);
            }

            const data = await response.json();
            await this.pollFileStatus(data.task_id, file.name);

        } catch (error) {
            this.updateFileProgress(file.name, 'error');
            throw error;
        }
    }

    updateFileProgress(filename, progress) {
        this.batchProgress.set(filename, progress);
        this.updateBatchProgressUI();
    }

    getTargetFormat(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        const allowedFormats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'pdf', 'docx', 'xlsx', 'pptx'];
        const targetFormat = allowedFormats.find(format => format === extension);
        return targetFormat;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showError(message) {
        const errorHtml = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
                <button class="retry-button" onclick="location.reload()">重试</button>
            </div>
        `;
        this.uploadContainer.innerHTML = errorHtml;
    }

    showBatchProgress() {
        const progressHtml = `
            <div class="batch-progress">
                <div class="progress-bar">
                    <div class="progress" id="batchProgress"></div>
                </div>
                <p class="status-text" id="batchStatusText">正在转换...</p>
            </div>
       ;
        this.uploadContainer.innerHTML = progressHtml;
    }

    async poll `FileStatus(taskId, filename) {
        const poll = async () => {
            try {
                const response = await fetch(`/status/${taskId}/`);
                const data = await response.json();

                switch (data.status) {
                    case 'completed':
                        this.updateFileProgress(filename, 'completed');
                        break;
                    case 'failed':
                        this.updateFileProgress(filename, 'error');
                        break;
                    case 'processing':
                        this.updateFileProgress(filename, data.progress || 50);
                        setTimeout(poll, 1000);
                        break;
                }
            } catch (error) {
                this.updateFileProgress(filename, 'error');
            }
        };

        poll();
    }

    updateBatchProgressUI() {
        const progressBar = document.getElementById('batchProgress');
        const statusText = document.getElementById('batchStatusText');
        if (progressBar && statusText) {
            const progress = Array.from(this.batchProgress.values()).reduce((a, b) => a + b, 0) / this.batchProgress.size;
            progressBar.style.width = `${progress}%`;
            statusText.textContent = `转换中 ${progress}%`;
        }
    }

    showBatchComplete() {
        const successHtml = `
            <div class="success-message">
                <i class="fas fa-check-circle"></i>
                <span>批量转换完成！</span>
                <button class="new-conversion-button" onclick="location.reload()">新的转换</button>
            </div>
        `;
        this.uploadContainer.innerHTML = successHtml;
    }
}

// 初始化上传器
document.addEventListener('DOMContentLoaded', () => {
    new FileUploader();
}); 