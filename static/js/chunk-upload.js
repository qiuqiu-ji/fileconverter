/**
 * 分片上传管理器
 */
class ChunkUploader {
    constructor(file, options = {}) {
        this.file = file;
        this.chunkSize = options.chunkSize || 2 * 1024 * 1024; // 默认2MB一片
        this.threads = options.threads || 3; // 默认3个并发上传线程
        this.retryTimes = options.retryTimes || 3; // 默认重试3次
        
        this.chunks = this.createChunks();
        this.uploadedChunks = new Set();
        this.failedChunks = new Map(); // 记录失败的分片及重试次数
        this.uploading = false;
        this.paused = false;

        // 进度回调
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
    }

    /**
     * 创建文件分片
     */
    createChunks() {
        const chunks = [];
        let start = 0;
        
        while (start < this.file.size) {
            const end = Math.min(start + this.chunkSize, this.file.size);
            chunks.push({
                index: chunks.length,
                start,
                end,
                size: end - start,
                uploaded: false
            });
            start = end;
        }
        
        return chunks;
    }

    /**
     * 开始上传
     */
    async start() {
        if (this.uploading) return;
        
        this.uploading = true;
        this.paused = false;

        try {
            // 获取或创建上传会话
            const session = await this.createUploadSession();
            
            // 恢复已上传的分片信息
            if (session.uploadedChunks) {
                session.uploadedChunks.forEach(index => {
                    this.uploadedChunks.add(index);
                    this.chunks[index].uploaded = true;
                });
            }

            // 开始并发上传
            while (!this.paused && this.hasRemainingChunks()) {
                const tasks = [];
                let running = 0;

                for (const chunk of this.chunks) {
                    if (running >= this.threads) break;
                    if (!chunk.uploaded && !this.failedChunks.has(chunk.index)) {
                        tasks.push(this.uploadChunk(chunk, session.uploadId));
                        running++;
                    }
                }

                if (tasks.length === 0) break;
                await Promise.all(tasks);
            }

            if (!this.paused && this.uploadedChunks.size === this.chunks.length) {
                // 所有分片上传完成，合并文件
                await this.completeUpload(session.uploadId);
                this.onComplete();
            }

        } catch (error) {
            this.onError(error);
        } finally {
            this.uploading = false;
        }
    }

    /**
     * 创建上传会话
     */
    async createUploadSession() {
        const response = await fetch('/api/upload/create-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: this.file.name,
                size: this.file.size,
                totalChunks: this.chunks.length
            })
        });

        if (!response.ok) {
            throw new Error('创建上传会话失败');
        }

        return await response.json();
    }

    /**
     * 上传单个分片
     */
    async uploadChunk(chunk, uploadId) {
        const retryCount = this.failedChunks.get(chunk.index) || 0;
        
        try {
            const formData = new FormData();
            formData.append('chunk', this.file.slice(chunk.start, chunk.end));
            formData.append('chunkIndex', chunk.index);
            formData.append('uploadId', uploadId);

            const response = await fetch('/api/upload/chunk', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('分片上传失败');
            }

            // 标记分片上传成功
            chunk.uploaded = true;
            this.uploadedChunks.add(chunk.index);
            this.failedChunks.delete(chunk.index);

            // 更新进度
            this.updateProgress();

        } catch (error) {
            if (retryCount < this.retryTimes) {
                // 记录失败次数，稍后重试
                this.failedChunks.set(chunk.index, retryCount + 1);
            } else {
                throw new Error(`分片${chunk.index}上传失败，已超过最大重试次数`);
            }
        }
    }

    /**
     * 完成上传
     */
    async completeUpload(uploadId) {
        const response = await fetch('/api/upload/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                uploadId,
                filename: this.file.name,
                totalChunks: this.chunks.length
            })
        });

        if (!response.ok) {
            throw new Error('文件合并失败');
        }

        return await response.json();
    }

    /**
     * 更新上传进度
     */
    updateProgress() {
        const progress = (this.uploadedChunks.size / this.chunks.length) * 100;
        this.onProgress(progress);
    }

    /**
     * 暂停上传
     */
    pause() {
        this.paused = true;
    }

    /**
     * 恢复上传
     */
    resume() {
        if (!this.uploading) {
            this.start();
        }
        this.paused = false;
    }

    /**
     * 检查是否还有未上传的分片
     */
    hasRemainingChunks() {
        return this.uploadedChunks.size < this.chunks.length;
    }

    /**
     * 获取上传状态
     */
    getStatus() {
        return {
            totalChunks: this.chunks.length,
            uploadedChunks: this.uploadedChunks.size,
            failedChunks: this.failedChunks.size,
            progress: (this.uploadedChunks.size / this.chunks.length) * 100,
            paused: this.paused,
            uploading: this.uploading
        };
    }
} 