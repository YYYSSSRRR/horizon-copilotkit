"""
CopilotKit Python 运行时

CopilotKit 运行时的 Python 实现，与 TypeScript 版本保持完全的 API 兼容性。

## 概述

CopilotKit Python Runtime 是一个强大的 AI 集成框架，让你能够轻松地将 AI 能力
集成到你的 Python 应用中。它提供了与前端 CopilotKit 组件的无缝集成。

## 核心功能

- 🚀 **完全兼容** - 与 TypeScript runtime 的 API 完全兼容
- 🔧 **多种适配器** - 支持 OpenAI、Anthropic、Google、DeepSeek、LangChain 等
- 🤖 **代理支持** - 支持 LangGraph、CrewAI 等代理框架
- 📊 **GraphQL API** - 提供完整的 GraphQL 接口
- 🔄 **流式响应** - 支持实时流式 AI 响应
- 🔗 **中间件系统** - 灵活的请求处理管道
- 🌐 **远程端点** - 支持 LangGraph Platform 等远程服务
- 🔧 **MCP 支持** - 模型上下文协议支持（实验性）

## 快速开始

```python
from copilotkit_runtime import CopilotRuntime, OpenAIAdapter, run_copilot_server

# 创建运行时和适配器
runtime = CopilotRuntime()
adapter = OpenAIAdapter(api_key="your-openai-api-key")

# 启动服务器
await run_copilot_server(runtime, adapter, port=8000)
```

## 主要组件

- `CopilotRuntime`: 核心运行时类
- `Action`: 定义可供 AI 调用的工具函数
- 各种适配器: 连接不同的 AI 服务提供商
- FastAPI 集成: 轻松部署和运行服务器
"""

from .runtime import CopilotRuntime
from .types import (
    Action,
    Parameter,
    Message,
    MessageRole,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage,
    AgentStateMessage,
    ImageMessage,
    CopilotRuntimeRequest,
    CopilotRuntimeResponse,
    Middleware,
    OnBeforeRequestHandler,
    OnAfterRequestHandler,
    ActionsConfiguration,
)
from .adapters import (
    CopilotServiceAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    GoogleAdapter,
    LangChainAdapter,
    DeepSeekAdapter,
    EmptyAdapter,
)
from .endpoints import (
    EndpointDefinition,
    EndpointType,
    CopilotKitEndpoint,
    LangGraphPlatformEndpoint,
    copilot_kit_endpoint,
    langgraph_platform_endpoint,
)
from .exceptions import (
    CopilotKitError,
    CopilotKitMisuseError,
    CopilotKitApiDiscoveryError,
    CopilotKitAgentDiscoveryError,
    CopilotKitLowLevelError,
)
from .fastapi_integration import (
    CopilotRuntimeFastAPI,
    copilot_runtime_fastapi_endpoint,
    create_copilot_app,
    run_copilot_server,
)

__version__ = "1.8.15"
__all__ = [
    # Core runtime
    "CopilotRuntime",
    
    # Types
    "Action",
    "Parameter",
    "Message",
    "MessageRole",
    "TextMessage",
    "ActionExecutionMessage",
    "ResultMessage",
    "AgentStateMessage",
    "ImageMessage",
    "CopilotRuntimeRequest",
    "CopilotRuntimeResponse",
    "Middleware",
    "OnBeforeRequestHandler",
    "OnAfterRequestHandler",
    "ActionsConfiguration",
    
    # Adapters
    "CopilotServiceAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GoogleAdapter",
    "LangChainAdapter",
    "DeepSeekAdapter",
    "EmptyAdapter",
    
    # Endpoints
    "EndpointDefinition",
    "EndpointType",
    "CopilotKitEndpoint",
    "LangGraphPlatformEndpoint",
    "copilot_kit_endpoint",
    "langgraph_platform_endpoint",
    
    # Exceptions
    "CopilotKitError",
    "CopilotKitMisuseError",
    "CopilotKitApiDiscoveryError",
    "CopilotKitAgentDiscoveryError",
    "CopilotKitLowLevelError",
    
    # FastAPI integration
    "CopilotRuntimeFastAPI",
    "copilot_runtime_fastapi_endpoint",
    "create_copilot_app",
    "run_copilot_server",
] 