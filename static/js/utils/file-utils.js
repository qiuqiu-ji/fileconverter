class FileUtils {
    /**
     * 获取文件格式
     * @param {File} file - 文件对象
     * @returns {string} 文件格式（小写）
     */
    static getFormat(file) {
        return file.name.split('.').pop().toLowerCase();
    }

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string} 格式化后的大小
     */
    static formatSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    /**
     * 获取文件图标
     * @param {string} format - 文件格式
     * @returns {string} Font Awesome图标类名
     */
    static getIcon(format) {
        const icons = {
            // 图片
            'jpg': 'fa-file-image',
            'jpeg': 'fa-file-image',
            'png': 'fa-file-image',
            'gif': 'fa-file-image',
            'bmp': 'fa-file-image',
            'svg': 'fa-file-image',
            
            // 文档
            'pdf': 'fa-file-pdf',
            'doc': 'fa-file-word',
            'docx': 'fa-file-word',
            'txt': 'fa-file-alt',
            'rtf': 'fa-file-alt',
            
            // 表格
            'xls': 'fa-file-excel',
            'xlsx': 'fa-file-excel',
            'csv': 'fa-file-csv',
            
            // 演示文稿
            'ppt': 'fa-file-powerpoint',
            'pptx': 'fa-file-powerpoint',
            
            // 压缩文件
            'zip': 'fa-file-archive',
            'rar': 'fa-file-archive',
            '7z': 'fa-file-archive',
            
            // 音频
            'mp3': 'fa-file-audio',
            'wav': 'fa-file-audio',
            'ogg': 'fa-file-audio',
            
            // 视频
            'mp4': 'fa-file-video',
            'avi': 'fa-file-video',
            'mov': 'fa-file-video',
            
            // 代码
            'html': 'fa-file-code',
            'css': 'fa-file-code',
            'js': 'fa-file-code',
            'json': 'fa-file-code',
            'xml': 'fa-file-code'
        };
        
        return icons[format.toLowerCase()] || 'fa-file';
    }

    /**
     * 检查文件类型是否支持
     * @param {string} format - 文件格式
     * @param {Array} supportedFormats - 支持的格式列表
     * @returns {boolean} 是否支持
     */
    static isSupported(format, supportedFormats) {
        return supportedFormats.includes(format.toLowerCase());
    }

    /**
     * 生成唯一文件ID
     * @returns {string} 唯一ID
     */
    static generateId() {
        return Math.random().toString(36).substr(2, 9);
    }

    /**
     * 计算文件的MD5哈希
     * @param {File} file - 文件对象
     * @returns {Promise<string>} MD5哈希值
     */
    static async calculateHash(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const buffer = e.target.result;
                    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
                    const hashArray = Array.from(new Uint8Array(hashBuffer));
                    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                    resolve(hashHex);
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsArrayBuffer(file);
        });
    }

    /**
     * 验证文件
     * @param {File} file - 文件对象
     * @param {Object} options - 验证选项
     * @returns {Object} 验证结果
     */
    static validateFile(file, options = {}) {
        const {
            maxSize = Infinity,
            allowedFormats = [],
            minSize = 0
        } = options;

        const result = {
            valid: true,
            errors: []
        };

        // 检查文件大小
        if (file.size > maxSize) {
            result.valid = false;
            result.errors.push(`File size exceeds limit of ${this.formatSize(maxSize)}`);
        }

        if (file.size < minSize) {
            result.valid = false;
            result.errors.push(`File size is below minimum of ${this.formatSize(minSize)}`);
        }

        // 检查文件格式
        if (allowedFormats.length > 0) {
            const format = this.getFormat(file);
            if (!this.isSupported(format, allowedFormats)) {
                result.valid = false;
                result.errors.push(`File format ${format} is not supported`);
            }
        }

        return result;
    }
} 