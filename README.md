# File Converter

在线文件转换工具，支持多种格式转换。

## 功能特点

- 支持多种文件格式转换
- 批量转换功能
- 用户认证和权限管理
- 文件安全扫描
- 转换历史记录
- 国际化支持

## 技术栈

- Django 4.2
- Celery
- Redis
- PostgreSQL
- Docker
- Nginx

## 开发环境设置

1. 克隆仓库：
bash
git clone https://github.com/yourusername/fileconverter.git
cd fileconverter
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，填写必要的配置
```

5. 运行数据库迁移：
```bash
python manage.py migrate
```

6. 创建超级用户：
```bash
python manage.py createsuperuser
```

7. 运行开发服务器：
```bash
python manage.py runserver
```

## 部署

使用Docker Compose部署：

```bash
# 构建镜像并启动容器
docker-compose up -d --build

# 执行数据库迁移
docker-compose exec web python manage.py migrate

# 收集静态文件
docker-compose exec web python manage.py collectstatic --noinput

# 创建超级用户
docker-compose exec web python manage.py createsuperuser
```

## 使用说明

1. 注册账号或登录
2. 上传需要转换的文件
3. 选择目标格式
4. 点击转换按钮
5. 等待转换完成后下载

## 支持的格式

- 文档：PDF, DOCX, TXT
- 图片：JPG, PNG, GIF, BMP
- 表格：XLSX, CSV
- 演示：PPTX

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证``` 