# CopilotKit Runtime Next

> 🚀 Python runtime for CopilotKit - 下一代无GraphQL依赖的运行时

## 概述

这是CopilotKit运行时的现代Python实现，通过REST API和WebSocket进行通信，专为与`@copilotkit/react-core-next`无缝协作而设计。

## ✨ 特性

- **🚫 无GraphQL**: 使用REST API + WebSocket进行通信
- **🏗️ 现代架构**: 基于FastAPI和async/await构建
- **🛡️ 类型安全**: 完整的类型注解系统
- **📡 流式支持**: 实时流式响应
- **🔌 适配器系统**: 可插拔的AI服务适配器
- **⚙️ 中间件支持**: 请求/响应中间件管道
- **🤖 内置适配器**: 支持OpenAI和DeepSeek

## 🚀 快速开始

### 基础用法

```python
from copilotkit_runtime import (
    CopilotRuntime, 
    OpenAIAdapter, 
    CopilotRuntimeServer,
    Action,
    Parameter,
    ParameterType
)

# 创建适配器
adapter = OpenAIAdapter(api_key="your-openai-key")

# 定义动作
async def get_weather(location: str) -> str:
    """获取指定地点的天气信息"""
    return f"{location}的天气：晴朗，25°C"

weather_action = Action(
    name="get_weather",
    description="获取天气信息",
    parameters=[
        Parameter(
            name="location",
            type=ParameterType.STRING,
            description="地点名称",
            required=True
        )
    ],
    handler=get_weather
)

# 创建运行时
runtime = CopilotRuntime(actions=[weather_action])

# 创建并运行服务器
server = CopilotRuntimeServer(runtime, adapter)
server.run(host="0.0.0.0", port=8000)
```

### 使用DeepSeek适配器

```python
from copilotkit_runtime import DeepSeekAdapter

# DeepSeek适配器
adapter = DeepSeekAdapter(
    api_key="your-deepseek-key",
    model="deepseek-chat"
)
```

### 使用Azure OpenAI

```python
from copilotkit_runtime import OpenAIAdapter

# Azure OpenAI适配器
adapter = OpenAIAdapter(
    api_key="your-azure-key",
    azure_endpoint="https://your-resource.openai.azure.com",
    azure_deployment="your-deployment-name",
    api_version="2024-02-15-preview"
)
```

### FastAPI集成

```python
from fastapi import FastAPI
from copilotkit_runtime import create_copilot_app

app = FastAPI()

# 创建CopilotKit子应用
copilot_app = create_copilot_app(runtime, adapter)

# 挂载到主应用
app.mount("/copilotkit", copilot_app)
```

## 📦 安装

```bash
pip install copilotkit-runtime-next
```

开发环境安装：

```bash
pip install copilotkit-runtime-next[dev]
```

## 🔧 API端点

服务器启动后，提供以下API端点：

- `GET /api/health` - 健康检查
- `POST /api/chat` - 聊天完成（非流式）
- `POST /api/chat/stream` - 聊天流式响应
- `GET /api/actions` - 列出可用动作
- `POST /api/actions/execute` - 执行动作
- `GET /api/agents` - 列出可用代理

## 🏗️ 架构

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   React Frontend    │───▶│   Runtime Server    │───▶│    AI Adapter       │
│ (react-core-next)   │    │   (FastAPI)         │    │  (OpenAI/DeepSeek)  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🔌 适配器

### 内置适配器

- **OpenAIAdapter**: 支持OpenAI和Azure OpenAI
- **DeepSeekAdapter**: 支持DeepSeek API

### 自定义适配器

```python
from copilotkit_runtime import CopilotServiceAdapter, AdapterRequest, AdapterResponse

class CustomAdapter(CopilotServiceAdapter):
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        # 实现你的逻辑
        pass
```

## 🧪 开发

```bash
# 克隆仓库
git clone https://github.com/CopilotKit/CopilotKit.git
cd CopilotKit/packages/runtime-next

# 安装依赖
poetry install

# 运行测试
poetry run pytest

# 代码格式化
poetry run black .
poetry run isort .

# 类型检查
poetry run mypy .
```

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE) 文件。

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解详情。

## 🔗 相关链接

- [CopilotKit 文档](https://docs.copilotkit.ai)
- [GitHub 仓库](https://github.com/CopilotKit/CopilotKit)
- [问题反馈](https://github.com/CopilotKit/CopilotKit/issues) 