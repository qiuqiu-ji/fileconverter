// 批量上传处理
class BatchUploader {
    constructor() {
        this.files = new Map();
        this.uploadQueue = [];
        this.isUploading = false;
        this.initElements();
        this.initEvents();
    }
    
    initElements() {
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.fileTable = document.getElementById('fileTable');
        this.startButton = document.getElementById('startConversion');
        this.clearButton = document.getElementById('clearAll');
    }
    
    initEvents() {
        // 拖放处理
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });
        
        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('dragover');
        });
        
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // 文件选择
        this.fileInput.addEventListener('change', () => {
            this.handleFiles(this.fileInput.files);
        });
        
        // 开始转换
        this.startButton.addEventListener('click', () => {
            this.startConversion();
        });
        
        // 清空列表
        this.clearButton.addEventListener('click', () => {
            this.clearFiles();
        });
    }
    
    handleFiles(fileList) {
        Array.from(fileList).forEach(file => {
            if (this.validateFile(file)) {
                this.addFile(file);
            }
        });
        this.updateUI();
    }
    
    validateFile(file) {
        // 检查文件大小
        const maxSize = 100 * 1024 * 1024; // 100MB
        if (file.size > maxSize) {
            this.showError(`文件 ${file.name} 太大`);
            return false;
        }
        
        // 检查文件类型
        const allowedTypes = new Set([
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'text/plain'
        ]);
        
        if (!allowedTypes.has(file.type)) {
            this.showError(`不支持的文件类型: ${file.name}`);
            return false;
        }
        
        return true;
    }
    
    addFile(file) {
        const fileId = Date.now() + Math.random();
        this.files.set(fileId, {
            id: fileId,
            file: file,
            status: 'pending',
            progress: 0
        });
        
        const row = this.createFileRow(fileId, file);
        this.fileTable.querySelector('tbody').appendChild(row);
    }
    
    createFileRow(fileId, file) {
        const row = document.createElement('tr');
        row.dataset.fileId = fileId;
        row.innerHTML = `
            <td>${file.name}</td>
            <td>${this.formatSize(file.size)}</td>
            <td class="status">等待中</td>
            <td class="progress-cell">
                <div class="progress">
                    <div class="progress-bar" role="progressbar"></div>
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-danger remove-file">
                    删除
                </button>
            </td>
        `;
        
        row.querySelector('.remove-file').addEventListener('click', () => {
            this.removeFile(fileId);
        });
        
        return row;
    }
    
    removeFile(fileId) {
        this.files.delete(fileId);
        const row = this.fileTable.querySelector(`tr[data-file-id="${fileId}"]`);
        if (row) {
            row.remove();
        }
        this.updateUI();
    }
    
    clearFiles() {
        this.files.clear();
        this.fileTable.querySelector('tbody').innerHTML = '';
        this.updateUI();
    }
    
    updateUI() {
        this.startButton.disabled = this.files.size === 0;
    }
    
    async startConversion() {
        if (this.isUploading) return;
        
        this.isUploading = true;
        this.startButton.disabled = true;
        
        const targetFormat = document.getElementById('targetFormat').value;
        const mergeFiles = document.getElementById('mergeFiles').checked;
        
        try {
            for (const [fileId, fileInfo] of this.files) {
                if (fileInfo.status === 'pending') {
                    await this.uploadAndConvert(fileId, fileInfo, targetFormat);
                }
            }
        } finally {
            this.isUploading = false;
            this.updateUI();
        }
    }
    
    async uploadAndConvert(fileId, fileInfo, targetFormat) {
        const formData = new FormData();
        formData.append('file', fileInfo.file);
        formData.append('target_format', targetFormat);
        
        try {
            // 上传文件
            const response = await fetch('/api/convert/', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            
            const data = await response.json();
            
            // 监听转换进度
            this.monitorProgress(fileId, data.task_id);
            
        } catch (error) {
            this.updateFileStatus(fileId, 'error', error.message);
        }
    }
    
    monitorProgress(fileId, taskId) {
        const ws = new WebSocket(
            `ws://${window.location.host}/ws/convert/${taskId}/`
        );
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateFileStatus(fileId, data.status, null, data.progress);
            
            if (['completed', 'failed'].includes(data.status)) {
                ws.close();
            }
        };
    }
    
    updateFileStatus(fileId, status, message = null, progress = 0) {
        const row = this.fileTable.querySelector(`tr[data-file-id="${fileId}"]`);
        if (!row) return;
        
        const statusCell = row.querySelector('.status');
        const progressBar = row.querySelector('.progress-bar');
        
        statusCell.textContent = this.getStatusText(status);
        progressBar.style.width = `${progress}%`;
        
        if (message) {
            statusCell.title = message;
        }
    }
    
    getStatusText(status) {
        const statusMap = {
            'pending': '等待中',
            'processing': '处理中',
            'completed': '已完成',
            'failed': '失败',
            'error': '错误'
        };
        return statusMap[status] || status;
    }
    
    formatSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }
    
    showError(message) {
        // 可以使用toast或其他通知组件
        alert(message);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.batchUploader = new BatchUploader();
}); 