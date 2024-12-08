class ConversionProgress {
    constructor(taskId) {
        this.taskId = taskId;
        this.socket = null;
        this.onProgress = null;
        this.onComplete = null;
        this.onError = null;
    }

    connect() {
        // 建立WebSocket连接
        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/conversion/${this.taskId}/`
        );

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.status) {
                case 'processing':
                    if (this.onProgress) {
                        this.onProgress(data.progress, data.message);
                    }
                    break;
                    
                case 'completed':
                    if (this.onComplete) {
                        this.onComplete(data.message);
                    }
                    this.disconnect();
                    break;
                    
                case 'failed':
                    if (this.onError) {
                        this.onError(data.message);
                    }
                    this.disconnect();
                    break;
            }
        };

        this.socket.onclose = () => {
            console.log('WebSocket连接已关闭');
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            if (this.onError) {
                this.onError('连接错误');
            }
        };
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// 使用示例
function startConversion(file) {
    // 创建转换任务
    fetch('/api/convert/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 创建进度监听器
        const progress = new ConversionProgress(data.task_id);
        
        // 设置回调
        progress.onProgress = (percent, message) => {
            updateProgressBar(percent);
            updateStatusText(message);
        };
        
        progress.onComplete = (message) => {
            showSuccess(message);
        };
        
        progress.onError = (error) => {
            showError(error);
        };
        
        // 建立连接
        progress.connect();
    })
    .catch(error => {
        showError('创建转换任务失败');
    });
} 