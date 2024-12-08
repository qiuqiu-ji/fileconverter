class FileConverter {
    constructor(options) {
        this.options = options;
        this.files = new Map();
        this.initElements();
        this.initEventListeners();
    }

    initElements() {
        // 上传区域
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        
        // 格式选择
        this.formatSelector = document.getElementById('formatSelector');
        this.targetFormat = document.getElementById('targetFormat');
        
        // 文件列表
        this.fileList = document.getElementById('fileList');
        
        // 按钮
        this.convertActions = document.getElementById('convertActions');
        this.convertBtn = document.getElementById('convertBtn');
        this.clearBtn = document.getElementById('clearBtn');
        
        // 进度区域
        this.progressArea = document.getElementById('progressArea');
        this.progressBar = this.progressArea.querySelector('.progress-bar');
        this.statusText = document.getElementById('statusText');
    }

    initEventListeners() {
        // 拖放处理
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('drag-over');
        });

        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('drag-over');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });

        // 文件选择
        this.fileInput.addEventListener('change', () => {
            this.handleFiles(this.fileInput.files);
        });

        // 转换按钮
        this.convertBtn.addEventListener('click', () => this.startConversion());
        this.clearBtn.addEventListener('click', () => this.clearFiles());
    }

    handleFiles(fileList) {
        Array.from(fileList).forEach(file => {
            // 检查文件大小
            if (file.size > this.options.maxFileSize) {
                this.showError(this.options.i18n.fileTooLarge);
                return;
            }

            // 检查文件格式
            const format = this.getFileFormat(file);
            if (!this.isSupportedFormat(format)) {
                this.showError(this.options.i18n.invalidFormat);
                return;
            }

            // 添加到文件列表
            const fileId = this.generateFileId();
            this.files.set(fileId, file);
            this.addFileToList(fileId, file);
        });

        if (this.files.size > 0) {
            this.formatSelector.style.display = 'block';
            this.convertActions.style.display = 'block';
        }
    }

    addFileToList(fileId, file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.fileId = fileId;

        fileItem.innerHTML = `
            <div class="file-icon">
                <i class="fas ${this.getFileIcon(file)}"></i>
            </div>
            <div class="file-info">
                <p class="file-name">${file.name}</p>
                <p class="file-size">${this.formatFileSize(file.size)}</p>
            </div>
            <div class="file-actions">
                <button class="btn btn-sm btn-outline-danger" onclick="converter.removeFile('${fileId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        this.fileList.appendChild(fileItem);
    }

    async startConversion() {
        const targetFormat = this.targetFormat.value;
        if (!targetFormat) {
            this.showError(this.options.i18n.selectFormat);
            return;
        }

        this.convertBtn.disabled = true;
        this.progressArea.style.display = 'block';
        this.progressBar.style.width = '0%';
        this.statusText.textContent = this.options.i18n.converting;

        try {
            for (const [fileId, file] of this.files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('target_format', targetFormat);

                // 上传文件
                const uploadResponse = await fetch(this.options.urls.upload, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.options.csrf_token
                    },
                    body: formData
                });

                if (!uploadResponse.ok) {
                    throw new Error(await uploadResponse.text());
                }

                const { task_id } = await uploadResponse.json();

                // 开始转换并监控进度
                await this.monitorConversion(task_id);
            }

            this.statusText.textContent = this.options.i18n.success;
            setTimeout(() => location.reload(), 1500);

        } catch (error) {
            this.showError(`${this.options.i18n.error} ${error.message}`);
            this.convertBtn.disabled = false;
        }
    }

    async monitorConversion(taskId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(
                `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}` +
                this.options.urls.status.replace('task_id', taskId)
            );

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.updateProgress(data.progress);
                
                if (data.status === 'completed') {
                    ws.close();
                    resolve();
                } else if (data.status === 'failed') {
                    ws.close();
                    reject(new Error(data.message));
                }
            };

            ws.onerror = () => {
                reject(new Error('WebSocket connection failed'));
            };
        });
    }

    updateProgress(progress) {
        this.progressBar.style.width = `${progress}%`;
        this.progressBar.setAttribute('aria-valuenow', progress);
    }

    removeFile(fileId) {
        this.files.delete(fileId);
        const fileItem = this.fileList.querySelector(`[data-file-id="${fileId}"]`);
        if (fileItem) {
            fileItem.remove();
        }

        if (this.files.size === 0) {
            this.formatSelector.style.display = 'none';
            this.convertActions.style.display = 'none';
        }
    }

    clearFiles() {
        this.files.clear();
        this.fileList.innerHTML = '';
        this.formatSelector.style.display = 'none';
        this.convertActions.style.display = 'none';
        this.progressArea.style.display = 'none';
        this.fileInput.value = '';
    }

    // 工具方法
    getFileFormat(file) {
        return file.name.split('.').pop().toLowerCase();
    }

    isSupportedFormat(format) {
        return this.options.supportedFormats.some(f => f.includes(format));
    }

    getFileIcon(file) {
        const format = this.getFileFormat(file);
        const icons = {
            'pdf': 'fa-file-pdf',
            'doc': 'fa-file-word',
            'docx': 'fa-file-word',
            'xls': 'fa-file-excel',
            'xlsx': 'fa-file-excel',
            'jpg': 'fa-file-image',
            'jpeg': 'fa-file-image',
            'png': 'fa-file-image',
            'gif': 'fa-file-image'
        };
        return icons[format] || 'fa-file';
    }

    formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    generateFileId() {
        return Math.random().toString(36).substr(2, 9);
    }

    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        this.uploadArea.parentNode.insertBefore(alert, this.uploadArea);
    }
} 