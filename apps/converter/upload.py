import os
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import hashlib
import logging

logger = logging.getLogger(__name__)

class UploadSessionManager:
    """上传会话管理器"""
    
    CHUNK_DIR = 'chunks'  # 分片存储目录
    SESSION_TIMEOUT = 24 * 60 * 60  # 会话有效期24小时
    
    def __init__(self):
        # 确保分片存储目录存在
        self.chunk_path = os.path.join(settings.MEDIA_ROOT, self.CHUNK_DIR)
        if not os.path.exists(self.chunk_path):
            os.makedirs(self.chunk_path)

    def create_session(self, filename, file_size, total_chunks):
        """创建上传会话"""
        session_id = str(uuid.uuid4())
        session = {
            'id': session_id,
            'filename': filename,
            'file_size': file_size,
            'total_chunks': total_chunks,
            'uploaded_chunks': set(),
            'created_at': datetime.now().isoformat(),
            'chunk_dir': os.path.join(self.chunk_path, session_id)
        }
        
        # 创建分片存储目录
        os.makedirs(session['chunk_dir'])
        
        # 缓存会话信息
        cache.set(f'upload_session_{session_id}', session, self.SESSION_TIMEOUT)
        
        return session

    def get_session(self, session_id):
        """获取上传会话"""
        return cache.get(f'upload_session_{session_id}')

    def update_session(self, session_id, chunk_index):
        """更新会话状态"""
        session = self.get_session(session_id)
        if session:
            session['uploaded_chunks'].add(chunk_index)
            cache.set(f'upload_session_{session_id}', session, self.SESSION_TIMEOUT)
        return session

    def save_chunk(self, session_id, chunk_index, chunk_file):
        """保存分片文件"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError('上传会话不存在或已过期')
            
        chunk_filename = f'chunk_{chunk_index}'
        chunk_path = os.path.join(session['chunk_dir'], chunk_filename)
        
        with open(chunk_path, 'wb') as f:
            for chunk in chunk_file.chunks():
                f.write(chunk)
                
        return self.update_session(session_id, chunk_index)

    def merge_chunks(self, session_id):
        """合并分片文件"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError('上传会话不存在或已过期')
            
        if len(session['uploaded_chunks']) != session['total_chunks']:
            raise ValueError('还有分片未上传完成')
            
        # 创建目标文件目录
        target_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 
                                datetime.now().strftime('%Y/%m/%d'))
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # 合并文件
        target_path = os.path.join(target_dir, session['filename'])
        with open(target_path, 'wb') as target_file:
            for i in range(session['total_chunks']):
                chunk_path = os.path.join(session['chunk_dir'], f'chunk_{i}')
                with open(chunk_path, 'rb') as chunk_file:
                    target_file.write(chunk_file.read())
                    
        # 清理分片文件
        self.cleanup_session(session_id)
        
        # 返回相对路径
        return os.path.relpath(target_path, settings.MEDIA_ROOT)

    def cleanup_session(self, session_id):
        """清理会话数据"""
        session = self.get_session(session_id)
        if session and os.path.exists(session['chunk_dir']):
            # 删除分片文件和目录
            for chunk_file in os.listdir(session['chunk_dir']):
                os.remove(os.path.join(session['chunk_dir'], chunk_file))
            os.rmdir(session['chunk_dir'])
            
        # 删除缓存
        cache.delete(f'upload_session_{session_id}')

    def cleanup_expired_sessions(self):
        """清理过期的会话"""
        expired_time = datetime.now() - timedelta(hours=24)
        
        # 遍历分片目录
        for session_id in os.listdir(self.chunk_path):
            session = self.get_session(session_id)
            if session:
                created_at = datetime.fromisoformat(session['created_at'])
                if created_at < expired_time:
                    self.cleanup_session(session_id) 

class ChunkUploadHandler:
    def __init__(self):
        self.settings = settings.CONVERSION_SETTINGS['upload']
        self.chunk_size = self.settings['chunk_size']
        self.session_timeout = self.settings['session_timeout']
        
    def handle_chunk(self, session_id, chunk_index, chunk_file):
        """处理分片上传"""
        try:
            # 获取会话
            session = self._get_session(session_id)
            if not session:
                raise ValueError("Invalid or expired session")
                
            # 验证分片
            chunk_hash = self._calculate_chunk_hash(chunk_file)
            if not self._validate_chunk(session, chunk_index, chunk_hash):
                raise ValueError("Invalid chunk")
                
            # 保存分片
            chunk_path = self._save_chunk(session, chunk_index, chunk_file)
            
            # 更新会话
            self._update_session(session, chunk_index, chunk_hash)
            
            return True
            
        except Exception as e:
            logger.error(f"Chunk upload failed: {str(e)}")
            raise
            
    def _calculate_chunk_hash(self, chunk_file):
        """计算分片哈希"""
        hasher = hashlib.md5()
        for chunk in chunk_file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest() 