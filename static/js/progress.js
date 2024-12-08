/**
 * 转换进度管理器
 */
class ConversionProgress {
    constructor(taskId) {
        this.taskId = taskId;
        this.progressBar = document.getElementById('progressBar');
        this.statusText = document.getElementById('statusText');
        this.socket = null;
        this.initWebSocket();
    }

    initWebSocket() {
        // 建立WebSocket连接
        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/conversion/${this.taskId}/`
        );

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateProgress(data);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.fallbackToPolling();
        };
    }

    updateProgress(data) {
        // 更新进度条
        if (this.progressBar) {
            this.progressBar.style.width = `${data.progress}%`;
        }

        // 更新状态文本
        if (this.statusText) {
            this.statusText.textContent = i18n.gettext(data.status_message);
        }

        // 处理完成状态
        if (data.status === 'completed') {
            this.handleComplete(data);
        } else if (data.status === 'failed') {
            this.handleError(data);
        }
    }

    handleComplete(data) {
        // 显示完成状态
        this.showSuccess(data.download_url);
        this.closeSocket();
    }

    handleError(data) {
        // 显示错误信息
        i18n.showError(data.error_code, data.error_details);
        this.closeSocket();
    }

    fallbackToPolling() {
        // WebSocket失败时回退到轮询
        const pollStatus = async () => {
            try {
                const response = await fetch(`/api/conversion/${this.taskId}/status/`);
                const data = await response.json();
                this.updateProgress(data);

                if (!['completed', 'failed'].includes(data.status)) {
                    setTimeout(pollStatus, 1000);
                }
            } catch (error) {
                console.error('轮询错误:', error);
            }
        };

        pollStatus();
    }

    closeSocket() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    showSuccess(downloadUrl) {
        const container = document.getElementById('conversionContainer');
        if (container) {
            container.innerHTML = `
                <div class="success-message">
                    <i class="fas fa-check-circle"></i>
                    <h3>${i18n.gettext('conversion_complete')}</h3>
                    <a href="${downloadUrl}" class="download-button" download>
                        ${i18n.gettext('download_file')}
                    </a>
                    <button onclick="location.reload()" class="new-conversion-button">
                        ${i18n.gettext('start_new')}
                    </button>
                </div>
            `;
        }
    }
}

// 添加相关的CSS样式
const style = document.createElement('style');
style.textContent = `
    .progress-container {
        margin: 20px 0;
        background: #f0f0f0;
        border-radius: 4px;
        overflow: hidden;
    }

    .progress-bar {
        width: 0;
        height: 20px;
        background: var(--primary-color);
        transition: width 0.3s ease;
    }

    .status-text {
        text-align: center;
        margin-top: 10px;
        color: #666;
    }

    .success-message {
        text-align: center;
        padding: 20px;
    }

    .success-message i {
        font-size: 48px;
        color: #28a745;
        margin-bottom: 10px;
    }

    .download-button,
    .new-conversion-button {
        display: inline-block;
        padding: 10px 20px;
        margin: 10px;
        border-radius: 4px;
        text-decoration: none;
        transition: background-color 0.3s ease;
    }

    .download-button {
        background: var(--primary-color);
        color: white;
    }

    .new-conversion-button {
        background: #6c757d;
        color: white;
    }
`;

document.head.appendChild(style); 