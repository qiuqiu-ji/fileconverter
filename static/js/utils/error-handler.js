class ErrorHandler {
    constructor(options = {}) {
        this.options = {
            logErrors: true,
            showNotifications: true,
            notificationDuration: 5000,
            ...options
        };
        
        this.errorTypes = new Map([
            ['ValidationError', {
                title: '验证错误',
                icon: 'fa-exclamation-circle',
                class: 'error'
            }],
            ['NetworkError', {
                title: '网络错误',
                icon: 'fa-wifi',
                class: 'error'
            }],
            ['AuthError', {
                title: '认证错误',
                icon: 'fa-lock',
                class: 'error'
            }],
            ['QuotaError', {
                title: '配额超限',
                icon: 'fa-chart-pie',
                class: 'warning'
            }],
            ['ConversionError', {
                title: '转换错误',
                icon: 'fa-exchange-alt',
                class: 'error'
            }]
        ]);
    }

    /**
     * 处理错误
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    handleError(error, context = {}) {
        // 获取错误类型信息
        const errorType = this.getErrorType(error);
        
        // 记录错误
        if (this.options.logErrors) {
            this.logError(error, errorType, context);
        }
        
        // 显示通知
        if (this.options.showNotifications) {
            this.showErrorNotification(error, errorType);
        }
        
        // 执行错误特定的处理
        this.handleSpecificError(error, errorType, context);
    }

    /**
     * 获取错误类型信息
     * @param {Error} error - 错误对象
     * @returns {Object} 错误类型信息
     */
    getErrorType(error) {
        const errorName = error.constructor.name;
        return this.errorTypes.get(errorName) || {
            title: '未知错误',
            icon: 'fa-exclamation-triangle',
            class: 'error'
        };
    }

    /**
     * 记录错误
     * @param {Error} error - 错误对象
     * @param {Object} errorType - 错误类型信息
     * @param {Object} context - 错误上下文
     */
    logError(error, errorType, context) {
        const errorData = {
            timestamp: new Date().toISOString(),
            type: error.constructor.name,
            message: error.message,
            stack: error.stack,
            context: {
                url: window.location.href,
                userAgent: navigator.userAgent,
                ...context
            }
        };
        
        // 发送错误日志到服务器
        APIUtils.post('/api/logs/error', errorData).catch(e => {
            console.error('Failed to log error:', e);
        });
        
        // 同时在控制台输出
        console.error('[ErrorHandler]', errorData);
    }

    /**
     * 显示错误通知
     * @param {Error} error - 错误对象
     * @param {Object} errorType - 错误类型信息
     */
    showErrorNotification(error, errorType) {
        UIUtils.showNotification(error.message, errorType.class, {
            title: errorType.title,
            icon: errorType.icon,
            duration: this.options.notificationDuration
        });
    }

    /**
     * 处理特定类型的错误
     * @param {Error} error - 错误对象
     * @param {Object} errorType - 错误类型信息
     * @param {Object} context - 错误上下文
     */
    handleSpecificError(error, errorType, context) {
        switch (error.constructor.name) {
            case 'AuthError':
                // 处理认证错误
                if (error.code === 'token_expired') {
                    this.handleTokenExpired();
                } else {
                    this.redirectToLogin();
                }
                break;
                
            case 'QuotaError':
                // 处理配额错误
                this.handleQuotaExceeded(error, context);
                break;
                
            case 'NetworkError':
                // 处理网络错误
                this.retryRequest(error, context);
                break;
                
            case 'ValidationError':
                // 处理验证错误
                this.handleValidationError(error, context);
                break;
                
            case 'ConversionError':
                // 处理转换错误
                this.handleConversionError(error, context);
                break;
        }
    }

    /**
     * 处理令牌过期
     */
    handleTokenExpired() {
        // 刷新令牌
        APIUtils.post('/api/auth/refresh-token')
            .then(() => {
                // 刷新成功，重试之前的请求
                window.location.reload();
            })
            .catch(() => {
                // 刷新失败，重定向到登录页
                this.redirectToLogin();
            });
    }

    /**
     * 重定向到登录页
     */
    redirectToLogin() {
        const returnUrl = encodeURIComponent(window.location.href);
        window.location.href = `/login?return_url=${returnUrl}`;
    }

    /**
     * 处理配额超限
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    handleQuotaExceeded(error, context) {
        UIUtils.confirm({
            title: '配额超限',
            message: '您的使用配额已超限，是否升级到高级版本？',
            confirmText: '升级',
            cancelText: '取消',
            type: 'warning'
        }).then(confirmed => {
            if (confirmed) {
                window.location.href = '/pricing';
            }
        });
    }

    /**
     * 重试请求
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    retryRequest(error, context) {
        if (context.retryCount < 3) {
            setTimeout(() => {
                context.retryFunc(context.retryCount + 1);
            }, 1000 * Math.pow(2, context.retryCount));
        }
    }

    /**
     * 处理验证错误
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    handleValidationError(error, context) {
        if (context.form) {
            // 显示表单错误
            Object.entries(error.errors).forEach(([field, message]) => {
                const input = context.form.querySelector(`[name="${field}"]`);
                if (input) {
                    input.classList.add('is-invalid');
                    const feedback = input.nextElementSibling;
                    if (feedback) {
                        feedback.textContent = message;
                    }
                }
            });
        }
    }

    /**
     * 处理转换错误
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    handleConversionError(error, context) {
        if (context.task) {
            // 更新任务状态
            context.task.status = 'failed';
            context.task.error = error.message;
            
            // 显示重试按钮
            if (context.taskElement) {
                const retryButton = document.createElement('button');
                retryButton.className = 'btn btn-warning btn-sm';
                retryButton.innerHTML = '<i class="fas fa-redo"></i> 重试';
                retryButton.onclick = () => context.retryTask(context.task);
                context.taskElement.appendChild(retryButton);
            }
        }
    }
} 