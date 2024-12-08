#!/bin/bash

# 停止并删除旧容器
docker-compose down

# 构建新镜像
docker-compose build

# 启动新容器
docker-compose up -d

# 执行数据库迁移
docker-compose exec web python manage.py migrate

# 收集静态文件
docker-compose exec web python manage.py collectstatic --noinput

# 编译翻译文件
docker-compose exec web python manage.py compilemessages

# 检查服务状态
docker-compose ps 