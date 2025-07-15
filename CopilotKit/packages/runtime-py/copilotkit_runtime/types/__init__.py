"""
CopilotKit Runtime Python - 类型系统

完整的类型定义，对标TypeScript版本的类型系统
"""

from .enums import (
    MessageRole,
    CopilotRequestType,
    ActionInputAvailability,
    MessageStatusCode,
    RuntimeEventTypes,
    MetaEventName,
    MessageType,
    LangGraphEventTypes,
    EndpointType
)

from .messages import (
    BaseMessage,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage,
    AgentStateMessage,
    ImageMessage,
    Message
)

from .status import (
    BaseMessageStatus,
    PendingMessageStatus,
    SuccessMessageStatus,
    FailedMessageStatus
)

from .adapters import (
    CopilotServiceAdapter,
    AdapterRequest,
    AdapterResponse,
    EmptyAdapter
)

from .events import (
    RuntimeEvent,
    RuntimeEventSource
)

from .actions import (
    Action,
    ActionInput,
    ActionResult,
    Parameter
)

from .runtime import (
    CopilotRuntimeRequest,
    CopilotResponse
)

__all__ = [
        # 枚举
    "MessageRole",
    "CopilotRequestType", 
    "ActionInputAvailability",
    "MessageStatusCode",
    "RuntimeEventTypes",
    "MetaEventName",
    "MessageType",
    "LangGraphEventTypes", 
    "EndpointType",
    
    # 消息类型
    "BaseMessage",
    "TextMessage",
    "ActionExecutionMessage",
    "ResultMessage",
    "AgentStateMessage",
    "ImageMessage",
    "Message",
    
    # 状态类型
    "BaseMessageStatus",
    "PendingMessageStatus",
    "SuccessMessageStatus",
    "FailedMessageStatus",
    
    # 适配器类型
    "CopilotServiceAdapter",
    "AdapterRequest",
    "AdapterResponse",
    "EmptyAdapter",
    
    # 事件类型
    "RuntimeEvent",
    "RuntimeEventSource",
    
    # 动作类型
    "Action",
    "ActionInput", 
    "ActionResult",
    "Parameter",
    
    # 运行时类型
    "CopilotRuntimeRequest",
    "CopilotResponse",
] 