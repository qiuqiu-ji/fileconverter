.PHONY: install test lint format clean deploy help

install:  ## 安装依赖
	pip install -r requirements.txt

test:  ## 运行测试
	pytest

lint:  ## 代码检查
	flake8 .
	black --check .
	isort --check-only .
	mypy .

format:  ## 格式化代码
	black .
	isort .

clean:  ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".tox" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	find . -type d -name "build" -exec rm -r {} +
	find . -type d -name "dist" -exec rm -r {} +

deploy:  ## 部署应用
	bash deploy.sh

migrations:  ## 创建数据库迁移
	python manage.py makemigrations

migrate:  ## 应用数据库迁移
	python manage.py migrate

messages:  ## 更新翻译文件
	python manage.py makemessages -l zh_Hans
	python manage.py compilemessages

shell:  ## 打开Django shell
	python manage.py shell

superuser:  ## 创建超级用户
	python manage.py createsuperuser

run:  ## 运行开发服务器
	python manage.py runserver

help:  ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

default: help 