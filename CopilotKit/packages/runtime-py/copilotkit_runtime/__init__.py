"""
CopilotKit Python Runtime

CopilotKit的Python运行时实现，基于FastAPI，无GraphQL依赖。

## 快速开始

```python
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter

# 创建运行时
runtime = CopilotRuntime()

# 配置DeepSeek适配器
deepseek_adapter = DeepSeekAdapter(
    api_key="your-deepseek-api-key",
    model="deepseek-chat"
)

# 使用适配器
runtime.use(deepseek_adapter)

# 注册动作
@runtime.action("get_weather", "获取天气信息")
async def get_weather(city: str):
    return f"{city}的天气很好"

# 启动服务器
if __name__ == "__main__":
    runtime.start(host="0.0.0.0", port=8000)
```

## 特性

- 🚀 基于FastAPI的高性能异步运行时
- 🔄 使用RxPY替代RxJS，保持功能逻辑一致性
- 📡 支持流式响应和事件源
- 🧩 与react-core-next无缝对接
- 🔌 支持DeepSeek等AI服务适配器
- 📝 完整的类型系统支持
"""

from .core import CopilotRuntime, CopilotResolver
from .types import *
from .streaming import StreamingResponse, MessageStreamer, EventSource
from .utils import random_id
from .integrations import CopilotRuntimeServer, create_copilot_app, create_copilot_runtime_server

# 版本信息
__version__ = "0.1.0"
__author__ = "CopilotKit Team"
__email__ = "team@copilotkit.dev"

# 公共接口
__all__ = [
    # 核心类
    "CopilotRuntime",
    "CopilotResolver",
    
    # 集成
    "CopilotRuntimeServer",
    "create_copilot_app",
    "create_copilot_runtime_server",
    
    # 流式处理
    "StreamingResponse",
    "MessageStreamer",
    "EventSource",
    
    # 工具函数
    "random_id",
    
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 类型（从types模块导入的所有类型）
    "MessageRole",
    "CopilotRequestType",
    "ActionInputAvailability", 
    "MessageStatusCode",
    "RuntimeEventTypes",
    "MetaEventName",
    "MessageType",
    "LangGraphEventTypes",
    "EndpointType",
    
    "BaseMessage",
    "TextMessage",
    "ActionExecutionMessage",
    "ResultMessage",
    "AgentStateMessage",
    "ImageMessage",
    "Message",
    
    "BaseMessageStatus",
    "PendingMessageStatus",
    "SuccessMessageStatus",
    "FailedMessageStatus",
    
    "CopilotServiceAdapter",
    "AdapterRequest",
    "AdapterResponse",
    "EmptyAdapter",
    
    "RuntimeEvent",
    "RuntimeEventSource",
    
    "Action",
    "ActionInput",
    "ActionResult",
    "Parameter",
    
    "CopilotRuntimeRequest",
    "CopilotResponse",
] 