# 建议的开发命令

## 开发工具命令
基于项目配置，以下是主要的开发命令：

### 代码质量
- `black .` - 代码格式化 (基于pyproject.toml配置)
- `flake8 .` - 代码风格检查
- `mypy .` - 类型检查

### 测试
- `pytest` - 运行所有测试
- `pytest -v` - 详细测试输出
- `pytest tests/` - 运行测试目录中的测试

### 安装依赖
- `pip install -r requirements.txt` - 安装生产依赖
- `pip install -e .[dev]` - 开发模式安装（包含开发依赖）
- `pip install -e .[redis,cli,dev]` - 安装所有可选依赖

### 运行应用
- `python main.py` - 启动FastAPI应用
- `uvicorn app.api.main:app --reload` - 开发模式启动
- `function-rag` - 使用CLI脚本（如果安装了cli依赖）

## 任务完成检查
完成编码任务后应该运行：
1. `black .` - 格式化代码
2. `flake8 .` - 检查代码风格 
3. `mypy .` - 类型检查
4. `pytest` - 运行测试