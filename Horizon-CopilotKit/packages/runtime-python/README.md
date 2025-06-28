# CopilotKit Python Runtime

CopilotKit Python Runtime 是 CopilotKit 的 Python 后端运行时实现，提供与 TypeScript 版本完全兼容的 API，支持多种 AI 服务适配器和强大的代理功能。

Horizon-CopilotKit/packages/runtime-python/
├── copilotkit_runtime/
│   ├── __init__.py           # 主导出文件
│   ├── runtime.py            # 核心 CopilotRuntime 类
│   ├── types.py              # 类型定义
│   ├── exceptions.py         # 异常类
│   ├── events.py             # 事件系统
│   ├── utils.py              # 工具函数
│   ├── endpoints.py          # 端点定义
│   ├── graphql_schema.py     # GraphQL Schema
│   ├── fastapi_integration.py # FastAPI 集成
│   └── adapters/             # 服务适配器
│       ├── __init__.py
│       ├── base.py           # 基础适配器接口
│       ├── openai_adapter.py
│       ├── anthropic_adapter.py
│       ├── google_adapter.py
│       └── langchain_adapter.py
├── examples/                 # 使用示例
│   ├── basic_example.py
│   └── langgraph_example.py
├── tests/                    # 测试文件
│   └── test_runtime.py
├── pyproject.toml            # Poetry 配置
├── README.md                 # 文档
├── CHANGELOG.md              # 更新日志
├── Makefile                  # 开发任务
└── .gitignore                # Git 忽略文件

## 特性

- 🚀 **完全兼容** - 与 TypeScript runtime 的 API 完全兼容
- 🔧 **多种适配器** - 支持 OpenAI、Anthropic、Google、DeepSeek、LangChain 等
- 🤖 **代理支持** - 支持 LangGraph、CrewAI 等代理框架
- 📊 **GraphQL API** - 提供完整的 GraphQL 接口
- 🔄 **流式响应** - 支持实时流式 AI 响应
- 🔗 **中间件系统** - 灵活的请求处理管道
- 🌐 **远程端点** - 支持 LangGraph Platform 等远程服务
- 🔧 **MCP 支持** - 模型上下文协议支持（实验性）

## 安装

```bash
pip install copilotkit-runtime
```

或使用 Poetry：

```bash
poetry add copilotkit-runtime
```

## 快速开始

### 基本使用

```python
from copilotkit_runtime import CopilotRuntime, OpenAIAdapter
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# 创建 runtime 实例
runtime = CopilotRuntime()

# 创建服务适配器
adapter = OpenAIAdapter(api_key="your-openai-api-key")

# 挂载 GraphQL 端点
runtime.mount_graphql(app, adapter, endpoint="/api/copilotkit")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 使用 Actions

```python
from copilotkit_runtime import CopilotRuntime, OpenAIAdapter, Action, Parameter

def get_weather(location: str) -> str:
    """获取天气信息"""
    return f"{location} 的天气是晴天"

# 定义 Action
weather_action = Action(
    name="get_weather",
    description="获取指定位置的天气信息",
    parameters=[
        Parameter(
            name="location",
            type="string",
            description="要查询天气的位置",
            required=True
        )
    ],
    handler=get_weather
)

# 创建带有 Actions 的 runtime
runtime = CopilotRuntime(actions=[weather_action])
```

### 使用中间件

```python
from copilotkit_runtime import CopilotRuntime, Middleware

async def before_request(options):
    print(f"处理请求: {options.thread_id}")

async def after_request(options):
    print(f"请求完成: {options.thread_id}")

middleware = Middleware(
    on_before_request=before_request,
    on_after_request=after_request
)

runtime = CopilotRuntime(middleware=middleware)
```

### 使用 LangGraph 代理

```python
from copilotkit_runtime import CopilotRuntime, LangGraphPlatformEndpoint

runtime = CopilotRuntime(
    remote_endpoints=[
        LangGraphPlatformEndpoint(
            deployment_url="https://your-langgraph-deployment.com",
            langsmith_api_key="your-langsmith-key",
            agents=[{
                "name": "my_agent",
                "description": "一个有用的 AI 代理"
            }]
        )
    ]
)
```

## API 参考

### CopilotRuntime

主要的运行时类，负责处理所有 AI 请求和响应。

#### 构造函数参数

- `actions` - 服务器端 Actions 列表
- `middleware` - 中间件配置
- `remote_endpoints` - 远程端点配置
- `agents` - 代理配置
- `observability` - 可观测性配置
- `mcp_servers` - MCP 服务器配置（实验性）

### 服务适配器

#### OpenAIAdapter

```python
from copilotkit_runtime import OpenAIAdapter

adapter = OpenAIAdapter(
    api_key="your-api-key",
    model="gpt-4o",
    organization="your-org-id"  # 可选
)
```

#### AnthropicAdapter

```python
from copilotkit_runtime import AnthropicAdapter

adapter = AnthropicAdapter(
    api_key="your-api-key",
    model="claude-3-5-sonnet-20241022"
)
```

#### GoogleAdapter

```python
from copilotkit_runtime import GoogleAdapter

adapter = GoogleAdapter(
    api_key="your-api-key",
    model="gemini-1.5-pro"
)
```

#### DeepSeekAdapter

```python
from copilotkit_runtime import DeepSeekAdapter

# 方法 1：直接使用 API Key
adapter = DeepSeekAdapter(
    api_key="your-deepseek-api-key",
    model="deepseek-chat"  # 或 "deepseek-coder", "deepseek-reasoner"
)

# 方法 2：使用预配置的 OpenAI 客户端
from openai import AsyncOpenAI

deepseek_client = AsyncOpenAI(
    api_key="your-deepseek-api-key",
    base_url="https://api.deepseek.com/v1"
)

adapter = DeepSeekAdapter(
    openai=deepseek_client,
    model="deepseek-coder"
)
```

#### LangChainAdapter

```python
from copilotkit_runtime import LangChainAdapter
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o")

adapter = LangChainAdapter(
    chain_fn=lambda messages, tools: model.bind_tools(tools).stream(messages)
)
```

## 与 TypeScript 版本的兼容性

这个 Python runtime 与 TypeScript 版本完全兼容：

- 相同的 GraphQL Schema
- 相同的 API 接口
- 相同的消息格式
- 相同的错误处理

你可以直接替换 TypeScript runtime 而无需修改前端代码。

## 开发指南

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/CopilotKit/CopilotKit.git
cd CopilotKit/Horizon-CopilotKit/packages/runtime-python

# 安装 Poetry（如果还未安装）
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install

# 激活虚拟环境
poetry shell
```

### 开发任务

```bash
# 运行测试套件
poetry run pytest

# 运行测试并显示覆盖率
poetry run pytest --cov=copilotkit_runtime

# 代码格式化
poetry run black .
poetry run isort .

# 代码检查
poetry run ruff check .

# 类型检查
poetry run mypy .

# 构建包
poetry build

# 运行示例
python examples/basic_example.py
python examples/deepseek_example.py
```

### 项目结构

```
copilotkit_runtime/
├── __init__.py          # 主包导出
├── runtime.py           # 核心运行时类
├── types.py            # 类型定义
├── events.py           # 事件系统
├── utils.py            # 工具函数
├── exceptions.py       # 异常定义
├── endpoints.py        # 端点定义
├── graphql_schema.py   # GraphQL Schema
├── fastapi_integration.py  # FastAPI 集成
└── adapters/           # 服务适配器
    ├── __init__.py
    ├── base.py         # 基础适配器
    ├── openai_adapter.py
    ├── anthropic_adapter.py
    ├── google_adapter.py
    ├── deepseek_adapter.py
    └── langchain_adapter.py
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解详情。 