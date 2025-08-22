# Function RAG Python 项目概述

## 项目目的
这是一个 Python RAG (Retrieval Augmented Generation) 系统，专门用于存储和查询 LLM 函数。它提供了一个基于 FastAPI 的 HTTP API 服务，用于管理和搜索函数定义。

## 技术栈
- **Web框架**: FastAPI + Uvicorn
- **数据验证**: Pydantic (v2.5.0+)
- **向量数据库**: Qdrant (v1.7.0)
- **AI/ML**: OpenAI API (v1.3.6)
- **数据处理**: NumPy, Pandas, scikit-learn
- **HTTP客户端**: httpx (v0.25.2)
- **缓存**: Redis (可选，v5.0.1)
- **日志**: Loguru (v0.7.2)
- **配置**: python-dotenv, pydantic-settings
- **CLI**: Typer + Rich (可选)

## 项目结构
```
CopilotKit/packages/function-rag-py/
├── app/                    # 主应用代码
│   ├── api/               # FastAPI 路由和API端点
│   ├── core/              # 核心业务逻辑
│   ├── models/            # 数据模型和模式
│   ├── services/          # 服务层（嵌入、存储、检索）
│   └── utils/             # 工具和辅助函数
├── examples/              # 使用示例
├── tests/                 # 测试代码
├── docs/                  # 文档
├── requirements.txt       # pip 依赖
├── pyproject.toml        # 项目配置和依赖
└── main.py               # 应用入口点
```

## Python 版本
支持 Python 3.9+