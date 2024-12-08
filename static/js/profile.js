/**
 * 个人中心页面的交互功能
 */
class ProfileManager {
    constructor() {
        // 初始化DOM元素
        this.editProfileBtn = document.getElementById('editProfileBtn');
        this.avatarUpload = document.getElementById('avatarUpload');
        this.formatFilter = document.getElementById('formatFilter');
        this.statusFilter = document.getElementById('statusFilter');
        this.historyList = document.querySelector('.history-list');

        // 绑定事件处理器
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // 编辑个人资料
        if (this.editProfileBtn) {
            this.editProfileBtn.addEventListener('click', () => this.handleEditProfile());
        }

        // 头像上传
        if (this.avatarUpload) {
            this.avatarUpload.addEventListener('change', (e) => this.handleAvatarUpload(e));
        }

        // 历史记录筛选
        if (this.formatFilter) {
            this.formatFilter.addEventListener('change', () => this.filterHistory());
        }
        if (this.statusFilter) {
            this.statusFilter.addEventListener('change', () => this.filterHistory());
        }

        // 删除历史记录
        document.querySelectorAll('.delete-button').forEach(button => {
            button.addEventListener('click', (e) => this.handleDeleteHistory(e));
        });
    }

    /**
     * 处理编辑个人资料
     */
    handleEditProfile() {
        // 创建编辑表单
        const formHtml = `
            <div class="edit-profile-form">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" name="username" value="${document.querySelector('.detail-item .value').textContent.trim()}">
                </div>
                <div class="form-group">
                    <label>邮箱</label>
                    <input type="email" name="email" value="${document.querySelectorAll('.detail-item .value')[1].textContent.trim()}">
                </div>
                <div class="form-actions">
                    <button type="button" class="save-button">保存</button>
                    <button type="button" class="cancel-button">取消</button>
                </div>
            </div>
        `;

        const userDetails = document.querySelector('.user-details');
        userDetails.innerHTML = formHtml;

        // 绑定保存和取消��钮事件
        userDetails.querySelector('.save-button').addEventListener('click', () => this.saveProfile());
        userDetails.querySelector('.cancel-button').addEventListener('click', () => location.reload());
    }

    /**
     * 保存个人资料
     */
    async saveProfile() {
        const username = document.querySelector('input[name="username"]').value;
        const email = document.querySelector('input[name="email"]').value;

        try {
            const response = await fetch('/api/profile/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ username, email })
            });

            if (response.ok) {
                location.reload();
            } else {
                const data = await response.json();
                alert(data.message || '更新失败');
            }
        } catch (error) {
            console.error('更新个人资料失败:', error);
            alert('更新失败，请稍后重试');
        }
    }

    /**
     * 处理头像上传
     */
    async handleAvatarUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // 验证��件类型和大小
        if (!file.type.startsWith('image/')) {
            alert('请上传图片文件');
            return;
        }

        if (file.size > 5 * 1024 * 1024) { // 5MB
            alert('图片大小不能超过5MB');
            return;
        }

        const formData = new FormData();
        formData.append('avatar', file);

        try {
            const response = await fetch('/api/profile/avatar/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });

            if (response.ok) {
                location.reload();
            } else {
                const data = await response.json();
                alert(data.message || '上传失败');
            }
        } catch (error) {
            console.error('上传头像失败:', error);
            alert('上传失败，请稍后重试');
        }
    }

    /**
     * 筛选历史记录
     */
    filterHistory() {
        const format = this.formatFilter.value;
        const status = this.statusFilter.value;

        document.querySelectorAll('.history-item').forEach(item => {
            const matchFormat = !format || item.dataset.format.startsWith(format);
            const matchStatus = !status || item.dataset.status === status;
            item.style.display = matchFormat && matchStatus ? 'flex' : 'none';
        });
    }

    /**
     * 处理删除历史记录
     */
    async handleDeleteHistory(event) {
        if (!confirm('确定要删除这条记录吗？')) {
            return;
        }

        const button = event.currentTarget;
        const historyId = button.dataset.id;

        try {
            const response = await fetch(`/api/history/${historyId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });

            if (response.ok) {
                button.closest('.history-item').remove();
                // 如果没有记录了，显示空状态
                if (!document.querySelector('.history-item')) {
                    this.showEmptyState();
                }
            } else {
                const data = await response.json();
                alert(data.message || '删除失败');
            }
        } catch (error) {
            console.error('删除历史记录失败:', error);
            alert('删除失败，请稍后重试');
        }
    }

    /**
     * 显示空状态
     */
    showEmptyState() {
        this.historyList.innerHTML = `
            <div class="empty-history">
                <i class="far fa-folder-open"></i>
                <p>暂无转换记录</p>
                <a href="/" class="start-convert-button">开始转换</a>
            </div>
        `;
    }

    /**
     * 获取CSRF Token
     */
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }
}

// 初始化个人中心管理器
document.addEventListener('DOMContentLoaded', () => {
    new ProfileManager();
}); 