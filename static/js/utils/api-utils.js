class APIUtils {
    /**
     * 发送API请求
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求结果
     */
    static async request(url, options = {}) {
        const {
            method = 'GET',
            data = null,
            headers = {},
            timeout = 30000,
            withCredentials = true
        } = options;

        // 添加CSRF令牌
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        // 设置默认请求头
        if (!headers['Content-Type'] && !(data instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        // 创建请求配置
        const config = {
            method,
            headers,
            credentials: withCredentials ? 'include' : 'same-origin'
        };

        // 添加请求体
        if (data) {
            config.body = data instanceof FormData ? data : JSON.stringify(data);
        }

        try {
            // 创建超��Promise
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Request timeout')), timeout);
            });

            // 发送请求
            const response = await Promise.race([
                fetch(url, config),
                timeoutPromise
            ]);

            // 检查响应状态
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // 解析响应
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();

        } catch (error) {
            // 处理错误
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * 发送GET请求
     * @param {string} url - 请求URL
     * @param {Object} params - 查询参数
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求结果
     */
    static async get(url, params = {}, options = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return await this.request(fullUrl, { ...options, method: 'GET' });
    }

    /**
     * 发送POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求结果
     */
    static async post(url, data = {}, options = {}) {
        return await this.request(url, { ...options, method: 'POST', data });
    }

    /**
     * 发送PUT请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求结果
     */
    static async put(url, data = {}, options = {}) {
        return await this.request(url, { ...options, method: 'PUT', data });
    }

    /**
     * 发送DELETE请求
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求结果
     */
    static async delete(url, options = {}) {
        return await this.request(url, { ...options, method: 'DELETE' });
    }

    /**
     * 上传文件
     * @param {string} url - 上传URL
     * @param {File|FileList} files - 文件对象
     * @param {Object} options - 上传选项
     * @returns {Promise} 上传结果
     */
    static async upload(url, files, options = {}) {
        const formData = new FormData();
        
        if (files instanceof FileList) {
            Array.from(files).forEach(file => {
                formData.append('files[]', file);
            });
        } else {
            formData.append('file', files);
        }

        // 添加其他字段
        if (options.data) {
            Object.entries(options.data).forEach(([key, value]) => {
                formData.append(key, value);
            });
        }

        return await this.post(url, formData, {
            ...options,
            headers: {
                ...options.headers,
                'Content-Type': undefined  // 让浏览器自动设置
            }
        });
    }

    /**
     * 下载文件
     * @param {string} url - 下载URL
     * @param {string} filename - 保存的文件名
     * @param {Object} options - 下载选项
     */
    static async download(url, filename, options = {}) {
        try {
            const response = await this.request(url, {
                ...options,
                responseType: 'blob'
            });

            // 创建下载链接
            const blob = new Blob([response]);
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = filename;

            // 触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // 清理
            window.URL.revokeObjectURL(downloadUrl);

        } catch (error) {
            console.error('Download failed:', error);
            throw error;
        }
    }
} 