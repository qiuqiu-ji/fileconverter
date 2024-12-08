class ChunkUploader {
    constructor(options = {}) {
        this.options = {
            chunkSize: 1024 * 1024 * 2, // 2MB
            concurrency: 3,
            retries: 3,
            retryDelay: 1000,
            ...options
        };
        
        this.activeUploads = new Map();
        this.uploadQueue = [];
    }

    /**
     * 开始上传文件
     * @param {File} file - 文件对象
     * @param {string} uploadUrl - 上传URL
     * @param {Object} metadata - 文件元数据
     * @returns {Promise} 上传结果
     */
    async upload(file, uploadUrl, metadata = {}) {
        const uploadId = this.generateUploadId();
        const chunks = this.createChunks(file);
        
        const uploadState = {
            file,
            uploadUrl,
            metadata,
            chunks,
            completedChunks: 0,
            failedChunks: [],
            progress: 0,
            status: 'pending',
            aborted: false
        };
        
        this.activeUploads.set(uploadId, uploadState);
        
        try {
            // 初始化上传会话
            const session = await this.initSession(uploadState);
            uploadState.sessionId = session.id;
            
            // 上传所有分片
            await this.uploadChunks(uploadState);
            
            // 完成上传
            if (!uploadState.aborted) {
                await this.completeUpload(uploadState);
                uploadState.status = 'completed';
                this.onProgress(uploadId, 100);
            }
            
            return {
                uploadId,
                success: !uploadState.aborted,
                response: uploadState.response
            };
            
        } catch (error) {
            uploadState.status = 'failed';
            uploadState.error = error;
            this.onError(uploadId, error);
            throw error;
            
        } finally {
            this.activeUploads.delete(uploadId);
        }
    }

    /**
     * 创建文件分片
     * @param {File} file - 文件对象
     * @returns {Array} 分片数组
     */
    createChunks(file) {
        const chunks = [];
        let start = 0;
        
        while (start < file.size) {
            const end = Math.min(start + this.options.chunkSize, file.size);
            chunks.push({
                start,
                end,
                blob: file.slice(start, end),
                attempts: 0
            });
            start = end;
        }
        
        return chunks;
    }

    /**
     * 初始化上传会话
     * @param {Object} uploadState - 上传状态
     * @returns {Promise} 会话信息
     */
    async initSession(uploadState) {
        const { file, metadata } = uploadState;
        
        const response = await APIUtils.post(uploadState.uploadUrl + '/init', {
            filename: file.name,
            size: file.size,
            type: file.type,
            chunks: uploadState.chunks.length,
            metadata
        });
        
        return response;
    }

    /**
     * 上传所有分片
     * @param {Object} uploadState - 上传状态
     * @returns {Promise} 上传结果
     */
    async uploadChunks(uploadState) {
        const workers = Array(this.options.concurrency).fill(null).map(() =>
            this.uploadChunkWorker(uploadState)
        );
        
        await Promise.all(workers);
        
        // 检查是否有失败的分片需要重试
        if (uploadState.failedChunks.length > 0 && !uploadState.aborted) {
            await this.retryFailedChunks(uploadState);
        }
    }

    /**
     * 分片上传工作器
     * @param {Object} uploadState - 上传状态
     */
    async uploadChunkWorker(uploadState) {
        while (uploadState.chunks.length > 0 && !uploadState.aborted) {
            const chunk = uploadState.chunks.shift();
            
            try {
                await this.uploadChunk(uploadState, chunk);
                uploadState.completedChunks++;
                this.updateProgress(uploadState);
                
            } catch (error) {
                chunk.attempts++;
                if (chunk.attempts < this.options.retries) {
                    uploadState.failedChunks.push(chunk);
                } else {
                    throw new Error(`Failed to upload chunk ${chunk.start}-${chunk.end}`);
                }
            }
        }
    }

    /**
     * 上传单个分片
     * @param {Object} uploadState - 上传状态
     * @param {Object} chunk - 分片信息
     * @returns {Promise} 上传结果
     */
    async uploadChunk(uploadState, chunk) {
        const formData = new FormData();
        formData.append('sessionId', uploadState.sessionId);
        formData.append('chunk', chunk.blob);
        formData.append('start', chunk.start);
        formData.append('end', chunk.end);
        
        const response = await APIUtils.post(
            uploadState.uploadUrl + '/chunk',
            formData
        );
        
        return response;
    }

    /**
     * 重试失败的分片
     * @param {Object} uploadState - 上传状态
     */
    async retryFailedChunks(uploadState) {
        while (uploadState.failedChunks.length > 0 && !uploadState.aborted) {
            const chunk = uploadState.failedChunks.shift();
            await new Promise(resolve => setTimeout(resolve, this.options.retryDelay));
            await this.uploadChunk(uploadState, chunk);
            uploadState.completedChunks++;
            this.updateProgress(uploadState);
        }
    }

    /**
     * 完成上传
     * @param {Object} uploadState - 上传状态
     * @returns {Promise} 完成结果
     */
    async completeUpload(uploadState) {
        const response = await APIUtils.post(
            uploadState.uploadUrl + '/complete',
            { sessionId: uploadState.sessionId }
        );
        
        uploadState.response = response;
        return response;
    }

    /**
     * 取消上传
     * @param {string} uploadId - 上传ID
     */
    abort(uploadId) {
        const uploadState = this.activeUploads.get(uploadId);
        if (uploadState) {
            uploadState.aborted = true;
            uploadState.status = 'aborted';
        }
    }

    /**
     * 更新上传进度
     * @param {Object} uploadState - 上传状态
     */
    updateProgress(uploadState) {
        const progress = Math.round(
            (uploadState.completedChunks / uploadState.chunks.length) * 100
        );
        uploadState.progress = progress;
        this.onProgress(uploadState.uploadId, progress);
    }

    /**
     * 生成上传ID
     * @returns {string} 上传ID
     */
    generateUploadId() {
        return Math.random().toString(36).substr(2, 9);
    }

    /**
     * 进度回调
     * @param {string} uploadId - 上传ID
     * @param {number} progress - 进度值
     */
    onProgress(uploadId, progress) {
        if (this.options.onProgress) {
            this.options.onProgress(uploadId, progress);
        }
    }

    /**
     * 错误回调
     * @param {string} uploadId - 上传ID
     * @param {Error} error - 错误对象
     */
    onError(uploadId, error) {
        if (this.options.onError) {
            this.options.onError(uploadId, error);
        }
    }
} 