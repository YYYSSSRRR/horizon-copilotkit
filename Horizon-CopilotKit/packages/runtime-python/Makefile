.PHONY: install dev test lint format clean build publish

# 安装依赖
install:
	poetry install

# 开发模式安装
dev:
	poetry install --with dev

# 运行测试
test:
	poetry run pytest tests/ -v

# 运行测试并生成覆盖率报告
test-cov:
	poetry run pytest tests/ --cov=copilotkit_runtime --cov-report=html --cov-report=term

# 代码检查
lint:
	poetry run mypy copilotkit_runtime/
	poetry run ruff check copilotkit_runtime/

# 代码格式化
format:
	poetry run black copilotkit_runtime/ tests/ examples/
	poetry run isort copilotkit_runtime/ tests/ examples/
	poetry run ruff check --fix copilotkit_runtime/

# 清理构建文件
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# 构建包
build: clean
	poetry build

# 发布到 PyPI
publish: build
	poetry publish

# 运行基本示例
example-basic:
	cd examples && python basic_example.py

# 运行 LangGraph 示例
example-langgraph:
	cd examples && python langgraph_example.py

# 检查所有
check: lint test

# 开发环境设置
setup-dev: dev
	poetry run pre-commit install 