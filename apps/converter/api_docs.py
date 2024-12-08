"""API文档生成器"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.urls import reverse

@api_view(['GET'])
def api_documentation(request):
    """生成API文档"""
    base_url = request.build_absolute_uri('/api/v1/')
    
    api_docs = {
        "api_version": "1.0",
        "base_url": base_url,
        "endpoints": {
            "文件转换": {
                "转换单个文件": {
                    "url": "/api/convert/",
                    "method": "POST",
                    "description": "转换单个文件到目标格式",
                    "parameters": {
                        "file": {
                            "type": "file",
                            "required": True,
                            "description": "要转换的文件"
                        },
                        "target_format": {
                            "type": "string",
                            "required": True,
                            "description": "目标格式，如: pdf, docx, jpg等"
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "转换成功",
                            "example": {
                                "task_id": "abc123",
                                "status": "success"
                            }
                        },
                        "400": {
                            "description": "请求错误",
                            "example": {
                                "error": "不支持的文件格式"
                            }
                        }
                    }
                },
                "批量转换": {
                    "url": "/api/convert/batch/",
                    "method": "POST",
                    "description": "批量转换多个文件",
                    "parameters": {
                        "files[]": {
                            "type": "array[file]",
                            "required": True,
                            "description": "要转换的文件列表"
                        },
                        "target_format": {
                            "type": "string",
                            "required": True,
                            "description": "目标格式"
                        }
                    }
                }
            },
            "文件上传": {
                "创建上传会话": {
                    "url": "/api/upload/create-session",
                    "method": "POST",
                    "description": "创建文件上传会话，支持断点续传",
                    "parameters": {
                        "filename": "string",
                        "size": "integer",
                        "total_chunks": "integer"
                    }
                },
                "上传分片": {
                    "url": "/api/upload/chunk",
                    "method": "POST",
                    "description": "上传文件分片",
                    "parameters": {
                        "chunk": "file",
                        "chunk_index": "integer",
                        "upload_id": "string"
                    }
                }
            },
            "转换状态": {
                "查询状态": {
                    "url": "/api/conversion/{task_id}/status/",
                    "method": "GET",
                    "description": "查询转换任务状态",
                    "parameters": {
                        "task_id": {
                            "type": "string",
                            "required": True,
                            "description": "转换任务ID"
                        }
                    }
                }
            },
            "文件预览": {
                "生成预览": {
                    "url": "/api/preview/generate/",
                    "method": "POST",
                    "description": "生成文件预览",
                    "parameters": {
                        "file": "file"
                    }
                },
                "获取预览": {
                    "url": "/api/preview/{filename}/",
                    "method": "GET",
                    "description": "获取文件预览"
                }
            }
        },
        "支持的格式": {
            "输入格式": [
                "pdf", "docx", "xlsx", "pptx",
                "jpg", "png", "gif", "bmp", "svg"
            ],
            "输出格式": [
                "pdf", "docx", "jpg", "png"
            ]
        },
        "错误码": {
            "400": "请求参数错误",
            "401": "未授权",
            "403": "权限不足",
            "404": "资源不存在",
            "413": "文件太大",
            "415": "不支持的文件类型",
            "500": "服务器内部错误",
            "503": "服务暂时不可用"
        }
    }
    
    return Response(api_docs) 