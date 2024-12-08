/**
 * 批量文件转换管理器
 */
class BatchConverter extends FileConverter {
    constructor(options) {
        super(options);
        this.totalFiles = 0;
        this.completedFiles = 0;
        this.failedFiles = 0;
    }

    initElements() {
        super.initElements();
        this.batchQuality = document.getElementById('batchQuality');
        this.batchDetailProgress = document.getElementById('batchDetailProgress');
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

        this.totalFiles = this.files.size;
        this.completedFiles = 0;
        this.failedFiles = 0;

        try {
            // 创建批量任务
            const batchResponse = await fetch(this.options.urls.convert, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.options.csrf_token
                },
                body: JSON.stringify({
                    target_format: targetFormat,
                    quality: this.batchQuality.value,
                    file_count: this.totalFiles
                })
            });

            if (!batchResponse.ok) {
                throw new Error(await batchResponse.text());
            }

            const { batch_id } = await batchResponse.json();

            // 上传所有文件
            const uploads = Array.from(this.files.values()).map(file => {
            const formData = new FormData();
            formData.append('file', file);
                formData.append('batch_id', batch_id);

                return fetch(this.options.urls.upload, {
                method: 'POST',
                    headers: {
                        'X-CSRFToken': this.options.csrf_token
                    },
                body: formData
                });
            });

            await Promise.all(uploads);

            // 监控批量转换进度
            await this.monitorBatchConversion(batch_id);

            this.statusText.textContent = this.options.i18n.success;
            setTimeout(() => location.reload(), 1500);

        } catch (error) {
            this.showError(`${this.options.i18n.error} ${error.message}`);
            this.convertBtn.disabled = false;
        }
    }

    async monitorBatchConversion(batchId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(
                `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}` +
                this.options.urls.status.replace('batch_id', batchId)
            );

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.updateBatchProgress(data);
                
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

    updateBatchProgress(data) {
        // 更新总进度
        this.progressBar.style.width = `${data.progress}%`;
        this.progressBar.setAttribute('aria-valuenow', data.progress);

        // 更新状态文本
        this.statusText.textContent = `${data.completed}/${data.total} files converted`;

        // 更��详细进度
        this.updateDetailProgress(data);
    }

    updateDetailProgress(data) {
        // 清除旧的进度信息
        this.batchDetailProgress.innerHTML = '';

        // 添加新的进度信息
        data.files.forEach(file => {
            const fileProgress = document.createElement('div');
            fileProgress.className = 'batch-file-progress mb-2';
            
            fileProgress.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span class="file-name">${file.name}</span>
                    <span class="file-status">
                        ${this.getStatusBadge(file.status)}
                    </span>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar ${this.getProgressBarClass(file.status)}"
                         role="progressbar"
                         style="width: ${file.progress}%"
                         aria-valuenow="${file.progress}"
                         aria-valuemin="0"
                         aria-valuemax="100">
                    </div>
                </div>
            `;

            this.batchDetailProgress.appendChild(fileProgress);
        });
    }

    getStatusBadge(status) {
        const badges = {
            'pending': '<span class="badge bg-secondary">Pending</span>',
            'processing': '<span class="badge bg-primary">Processing</span>',
            'completed': '<span class="badge bg-success">Completed</span>',
            'failed': '<span class="badge bg-danger">Failed</span>'
        };
        return badges[status] || badges.pending;
    }

    getProgressBarClass(status) {
        const classes = {
            'pending': 'bg-secondary',
            'processing': 'bg-primary progress-bar-striped progress-bar-animated',
            'completed': 'bg-success',
            'failed': 'bg-danger'
        };
        return classes[status] || classes.pending;
    }
} 