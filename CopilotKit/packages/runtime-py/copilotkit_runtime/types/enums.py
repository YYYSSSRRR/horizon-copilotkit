"""
枚举类型定义

对标TypeScript runtime中的所有枚举类型
"""

from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    DEVELOPER = "developer"


class CopilotRequestType(str, Enum):
    """Copilot请求类型枚举"""
    CHAT = "Chat"
    TASK = "Task"
    TEXTAREA_COMPLETION = "TextareaCompletion"
    TEXTAREA_POPOVER = "TextareaPopover"
    SUGGESTION = "Suggestion"


class ActionInputAvailability(str, Enum):
    """动作输入可用性枚举"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    REMOTE = "remote"


class MessageStatusCode(str, Enum):
    """消息状态码枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class RuntimeEventTypes(str, Enum):
    """运行时事件类型枚举"""
    TEXT_MESSAGE_START = "TextMessageStart"
    TEXT_MESSAGE_CONTENT = "TextMessageContent"
    TEXT_MESSAGE_END = "TextMessageEnd"
    ACTION_EXECUTION_START = "ActionExecutionStart"
    ACTION_EXECUTION_ARGS = "ActionExecutionArgs"
    ACTION_EXECUTION_END = "ActionExecutionEnd"
    ACTION_EXECUTION_RESULT = "ActionExecutionResult"
    AGENT_STATE_MESSAGE = "AgentStateMessage"
    META_EVENT = "MetaEvent"


class MetaEventName(str, Enum):
    """元事件名称枚举"""
    LANGGRAPH_INTERRUPT_EVENT = "LangGraphInterruptEvent"
    COPILOTKIT_LANGGRAPH_INTERRUPT_EVENT = "CopilotKitLangGraphInterruptEvent"
    LANGGRAPH_INTERRUPT_RESUME_EVENT = "LangGraphInterruptResumeEvent"


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT_MESSAGE = "TextMessage"
    ACTION_EXECUTION_MESSAGE = "ActionExecutionMessage"
    RESULT_MESSAGE = "ResultMessage"
    AGENT_STATE_MESSAGE = "AgentStateMessage"
    IMAGE_MESSAGE = "ImageMessage"


class LangGraphEventTypes(str, Enum):
    """LangGraph事件类型枚举"""
    ON_CHAIN_START = "on_chain_start"
    ON_CHAIN_STREAM = "on_chain_stream"
    ON_CHAIN_END = "on_chain_end"
    ON_CHAT_MODEL_START = "on_chat_model_start"
    ON_CHAT_MODEL_STREAM = "on_chat_model_stream"
    ON_CHAT_MODEL_END = "on_chat_model_end"
    ON_TOOL_START = "on_tool_start"
    ON_TOOL_END = "on_tool_end"
    ON_COPILOTKIT_STATE_SYNC = "on_copilotkit_state_sync"
    ON_COPILOTKIT_EMIT_MESSAGE = "on_copilotkit_emit_message"
    ON_COPILOTKIT_EMIT_TOOL_CALL = "on_copilotkit_emit_tool_call"
    ON_CUSTOM_EVENT = "on_custom_event"
    ON_INTERRUPT = "on_interrupt"
    ON_COPILOTKIT_INTERRUPT = "on_copilotkit_interrupt"


class EndpointType(str, Enum):
    """端点类型枚举"""
    COPILOTKIT = "copilotkit"
    LANGGRAPH_PLATFORM = "langgraph_platform" 