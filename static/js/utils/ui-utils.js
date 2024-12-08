class UIUtils {
    /**
     * 显示通知
     * @param {string} message - 消息内容
     * @param {string} type - 通知类型 (success/error/warning/info)
     * @param {Object} options - 配置选项
     */
    static showNotification(message, type = 'info', options = {}) {
        const {
            duration = 3000,
            position = 'top-right',
            closable = true
        } = options;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type} notification-${position} fade-in`;
        
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
                ${closable ? '<button class="notification-close">&times;</button>' : ''}
            </div>
        `;

        document.body.appendChild(notification);

        // 添加关闭按钮事件
        if (closable) {
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => this.closeNotification(notification));
        }

        // 自动关闭
        if (duration > 0) {
            setTimeout(() => this.closeNotification(notification), duration);
        }
    }

    /**
     * 关闭通知
     * @param {HTMLElement} notification - 通知元素
     */
    static closeNotification(notification) {
        notification.classList.remove('fade-in');
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }

    /**
     * 获取通知图标
     * @param {string} type - 通知类型
     * @returns {string} Font Awesome图标类名
     */
    static getNotificationIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    /**
     * 显示加载中状态
     * @param {HTMLElement} element - 目标元素
     * @param {string} text - 加载文本
     */
    static showLoading(element, text = 'Loading...') {
        element.classList.add('loading');
        element.dataset.originalHtml = element.innerHTML;
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            <span>${text}</span>
        `;
        element.disabled = true;
    }

    /**
     * 隐藏加载中状态
     * @param {HTMLElement} element - 目标元素
     */
    static hideLoading(element) {
        element.classList.remove('loading');
        element.innerHTML = element.dataset.originalHtml;
        element.disabled = false;
        delete element.dataset.originalHtml;
    }

    /**
     * 创建确认对话框
     * @param {Object} options - 配置选项
     * @returns {Promise} 确认结果
     */
    static confirm(options = {}) {
        const {
            title = 'Confirm',
            message = 'Are you sure?',
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            type = 'primary'
        } = options;

        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                ${cancelText}
                            </button>
                            <button type="button" class="btn btn-${type}" data-action="confirm">
                                ${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();

            // 确认按钮事件
            modal.querySelector('[data-action="confirm"]').addEventListener('click', () => {
                modalInstance.hide();
                resolve(true);
            });

            // 取消和关闭事件
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
                resolve(false);
            });
        });
    }
} 