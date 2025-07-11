"""
CopilotKit Runtime Next - Python实现。

这是CopilotKit运行时的Python实现，不依赖GraphQL，与react-core-next无缝对接。

主要特性：
- 基于REST API + WebSocket架构
- 支持流式响应
- 内置DeepSeek和OpenAI适配器
- FastAPI集成
- 完整的类型系统
- 中间件支持
"""

# 核心运行时
from .runtime import CopilotRuntime
from .runtime.enhanced_copilot_runtime import EnhancedCopilotRuntime, create_enhanced_runtime

# 类型系统
from .types import *

# 事件系统
from .events import *
from .events.enhanced_runtime_events import (
    EnhancedRuntimeEventSource,
    AsyncRepeater,
    MessageStreamProcessor,
    MessageStatus,
    SuccessMessageStatus,
    FailedMessageStatus
)

# 中间件系统
from .middleware.enhanced_middleware import (
    EnhancedMiddlewareChain,
    BaseMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    AuthenticationMiddleware,
    RateLimitMiddleware,
    MiddlewareBuilder,
    create_default_middleware_chain,
    create_production_middleware_chain
)

# 适配器
from .adapters import DeepSeekAdapter, OpenAIAdapter

# 集成
from .integrations import CopilotRuntimeServer, create_copilot_app

# 工具函数
from .utils import *

__version__ = "1.8.15-next.0"

__all__ = [
    # 核心类
    "CopilotRuntime",
    "EnhancedCopilotRuntime",
    "create_enhanced_runtime",
    
    # 适配器
    "DeepSeekAdapter", 
    "OpenAIAdapter",
    "CopilotServiceAdapter",
    
    # 服务器集成
    "CopilotRuntimeServer",
    "create_copilot_app",
    
    # 增强事件系统
    "EnhancedRuntimeEventSource",
    "AsyncRepeater",
    "MessageStreamProcessor",
    "MessageStatus",
    "SuccessMessageStatus",
    "FailedMessageStatus",
    
    # 增强中间件系统
    "EnhancedMiddlewareChain",
    "BaseMiddleware",
    "LoggingMiddleware",
    "MetricsMiddleware",
    "AuthenticationMiddleware",
    "RateLimitMiddleware",
    "MiddlewareBuilder",
    "create_default_middleware_chain",
    "create_production_middleware_chain",
    
    # 类型（从各模块导出）
    "Action",
    "ActionResult",
    "Parameter",
    "ParameterType",
    "Message",
    "TextMessage",
    "ActionExecutionMessage",
    "ResultMessage",
    "MessageRole",
    "Agent",
    "AgentState",
    "Middleware",
    "RuntimeConfig",
    "RequestContext",
    "CopilotRuntimeRequest",
    "CopilotRuntimeResponse",
    
    # 事件
    "RuntimeEvent",
    "RuntimeEventSource",
    
    # 工具
    "generate_id",
] 