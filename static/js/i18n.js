// 获取当前语言
const currentLanguage = document.documentElement.lang;

// 翻译字典
const translations = {
    'zh-hans': {
        'uploading': '上传中...',
        'converting': '转换中...',
        'success': '转换成功！',
        'error': '转换失败：',
        'file_too_large': '文件太大',
        'invalid_format': '不支持的格式',
        'network_error': '网络错误',
        'server_error': '服务器错误',
        'unknown_error': '未知错误',
        'preparing': '准备中...',
        'processing': '处理中...',
        'finalizing': '完成中...',
        'ready': '准备就绪',
        'confirm_delete': '确定要删除这条记录吗？',
        'confirm_cancel': '确定要取消转换吗？',
        'select_format': '请选择目标格式',
        'select_file': '请选择文件',
        'start': '开始',
        'cancel': '取消',
        'retry': '重试',
        'close': '关闭',
        'confirm': '确定',
    },
    'zh-hant': {
        'uploading': '上傳中...',
        'converting': '轉換中...',
        'success': '轉換成功！',
        'error': '轉換失敗：',
        'file_too_large': '文件太大',
        'invalid_format': '不支持的格式',
        'network_error': '网络错误',
        'server_error': '服务器错误',
        'unknown_error': '未知错误',
        'preparing': '准备中...',
        'processing': '处理中...',
        'finalizing': '完成中...',
        'ready': '准备就绪',
        'confirm_delete': '确定要删除这条记录吗？',
        'confirm_cancel': '确定要取消转换吗？',
        'select_format': '请选择目标格式',
        'select_file': '请选择文件',
        'start': '开始',
        'cancel': '取消',
        'retry': '重试',
        'close': '关闭',
        'confirm': '确定',
    },
    'ja': {
        'uploading': 'アップロード中...',
        'converting': '変換中...',
        'success': '変換成功！',
        'error': '変換失敗：',
        'file_too_large': 'ファイルが大きすぎます',
        'invalid_format': 'サポートされていない形式',
        'network_error': 'ネットワークエラー',
        'server_error': 'サーバーエラー',
        'unknown_error': '未知のエラー',
        'preparing': '準備中...',
        'processing': '処理中...',
        'finalizing': '完了中...',
        'ready': '準備完了',
        'confirm_delete': 'このレコードを削除してもよろしいですか？',
        'confirm_cancel': '変換をキャンセルしてもよろしいですか？',
        'select_format': '変換先の形式を選択してください',
        'select_file': 'ファイルを選択してください',
        'start': '開始',
        'cancel': 'キャンセル',
        'retry': '再試行',
        'close': '閉じる',
        'confirm': '確認',
    },
    'en': {
        'uploading': 'Uploading...',
        'converting': 'Converting...',
        'success': 'Conversion successful!',
        'error': 'Conversion failed: ',
        'file_too_large': 'File is too large',
        'invalid_format': 'Unsupported format',
        'network_error': 'Network error',
        'server_error': 'Server error',
        'unknown_error': 'Unknown error',
        'preparing': 'Preparing...',
        'processing': 'Processing...',
        'finalizing': 'Finalizing...',
        'ready': 'Ready',
        'confirm_delete': 'Are you sure you want to delete this record?',
        'confirm_cancel': 'Are you sure you want to cancel the conversion?',
        'select_format': 'Please select target format',
        'select_file': 'Please select a file',
        'start': 'Start',
        'cancel': 'Cancel',
        'retry': 'Retry',
        'close': 'Close',
        'confirm': 'Confirm',
    }
};

// 翻译函数
function gettext(key) {
    return translations[currentLanguage]?.[key] || key;
} 

// 扩展翻译函数
const i18n = {
    gettext(key, params = {}) {
        let text = translations[currentLanguage]?.[key] || key;
        // 支持参数替换，例如：'Hello {name}' -> 'Hello John'
        Object.entries(params).forEach(([key, value]) => {
            text = text.replace(`{${key}}`, value);
        });
        return text;
    },
    
    // 格式化日期
    formatDate(date, format = 'long') {
        const options = {
            short: { year: 'numeric', month: 'short', day: 'numeric' },
            long: { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }
        };
        return new Date(date).toLocaleDateString(currentLanguage, options[format]);
    },
    
    // 格式化文件大小
    formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    },

    // 获取用户首选语言
    getPreferredLanguage() {
        return localStorage.getItem('preferred_language') || 
               document.documentElement.lang || 
               navigator.language.toLowerCase();
    },

    // 设置用户首选语言
    setPreferredLanguage(lang) {
        localStorage.setItem('preferred_language', lang);
        location.reload();
    }
};

// 扩展错误消息
const errorMessages = {
    'zh-hans': {
        'network_timeout': '网络连接超时，请检查网络设置',
        'server_busy': '服务器繁忙，请稍后重试',
        'invalid_response': '服务器响应异常',
        'upload_interrupted': '上传被中断',
        'download_failed': '下载失败',
    },
    'zh-hant': {
        'network_timeout': '網路連接超時，請檢查網路設定',
        'server_busy': '伺服器繁忙，請稍後重試',
        'invalid_response': '伺服器回應異常',
        'upload_interrupted': '上傳被中斷',
        'download_failed': '下載失敗',
    },
    'ja': {
        'network_timeout': 'ネットワーク接続がタイムアウトしました',
        'server_busy': 'サーバーが混雑しています。後でお試しください',
        'invalid_response': 'サーバーの応答が異常です',
        'upload_interrupted': 'アップロードが中断されました',
        'download_failed': 'ダウンロードに失敗しました',
    },
    'en': {
        'network_timeout': 'Network connection timeout, please check your network settings',
        'server_busy': 'Server is busy, please try again later',
        'invalid_response': 'Invalid server response',
        'upload_interrupted': 'Upload was interrupted',
        'download_failed': 'Download failed',
    }
};

// 扩展i18n对象
Object.assign(i18n, {
    // 获取错误消息
    getErrorMessage(code, params = {}) {
        const message = errorMessages[currentLanguage]?.[code] || code;
        return this.gettext(message, params);
    },

    // 显示错误提示
    showError(code, params = {}) {
        const message = this.getErrorMessage(code, params);
        // 这里可以集成你的提示UI组件
        alert(message);
    },

    // 格式化数字
    formatNumber(number, options = {}) {
        return new Intl.NumberFormat(currentLanguage, options).format(number);
    },

    // 格式化货币
    formatCurrency(amount, currency = 'CNY') {
        return new Intl.NumberFormat(currentLanguage, {
            style: 'currency',
            currency: currency
        }).format(amount);
    }
});

// 导出国际化工具
window.i18n = i18n; 