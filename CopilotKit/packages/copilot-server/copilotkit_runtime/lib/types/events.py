"""Event type definitions."""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel
from enum import Enum


class RuntimeEventTypes(str, Enum):
    """Runtime event types enumeration."""
    TEXT_MESSAGE_START = "TextMessageStart"
    TEXT_MESSAGE_CONTENT = "TextMessageContent"
    TEXT_MESSAGE_END = "TextMessageEnd"
    ACTION_EXECUTION_START = "ActionExecutionStart"
    ACTION_EXECUTION_ARGS = "ActionExecutionArgs"
    ACTION_EXECUTION_END = "ActionExecutionEnd"
    ACTION_EXECUTION_RESULT = "ActionExecutionResult"
    AGENT_STATE_MESSAGE = "AgentStateMessage"
    META_EVENT = "MetaEvent"


class RuntimeMetaEventName(str, Enum):
    """Runtime meta event name enumeration."""
    LANGGRAPH_INTERRUPT_EVENT = "LangGraphInterruptEvent"
    COPILOTKIT_LANGGRAPH_INTERRUPT_EVENT = "CopilotKitLangGraphInterruptEvent"


class BaseRuntimeEvent(BaseModel):
    """Base runtime event."""
    type: RuntimeEventTypes


class TextMessageStartEvent(BaseRuntimeEvent):
    """Text message start event."""
    type: RuntimeEventTypes = RuntimeEventTypes.TEXT_MESSAGE_START
    message_id: str
    parent_message_id: Optional[str] = None


class TextMessageContentEvent(BaseRuntimeEvent):
    """Text message content event."""
    type: RuntimeEventTypes = RuntimeEventTypes.TEXT_MESSAGE_CONTENT
    message_id: str
    content: str


class TextMessageEndEvent(BaseRuntimeEvent):
    """Text message end event."""
    type: RuntimeEventTypes = RuntimeEventTypes.TEXT_MESSAGE_END
    message_id: str


class ActionExecutionStartEvent(BaseRuntimeEvent):
    """Action execution start event."""
    type: RuntimeEventTypes = RuntimeEventTypes.ACTION_EXECUTION_START
    action_execution_id: str
    action_name: str
    parent_message_id: Optional[str] = None


class ActionExecutionArgsEvent(BaseRuntimeEvent):
    """Action execution arguments event."""
    type: RuntimeEventTypes = RuntimeEventTypes.ACTION_EXECUTION_ARGS
    action_execution_id: str
    args: str


class ActionExecutionEndEvent(BaseRuntimeEvent):
    """Action execution end event."""
    type: RuntimeEventTypes = RuntimeEventTypes.ACTION_EXECUTION_END
    action_execution_id: str


class ActionExecutionResultEvent(BaseRuntimeEvent):
    """Action execution result event."""
    type: RuntimeEventTypes = RuntimeEventTypes.ACTION_EXECUTION_RESULT
    action_execution_id: str
    action_name: str
    result: Any


class AgentStateMessageEvent(BaseRuntimeEvent):
    """Agent state message event."""
    type: RuntimeEventTypes = RuntimeEventTypes.AGENT_STATE_MESSAGE
    thread_id: str
    agent_name: str
    node_name: str
    run_id: str
    active: bool
    state: Dict[str, Any]
    running: bool


class MetaEvent(BaseRuntimeEvent):
    """Meta event."""
    type: RuntimeEventTypes = RuntimeEventTypes.META_EVENT
    name: RuntimeMetaEventName
    data: Optional[Dict[str, Any]] = None
    value: Optional[Any] = None


# Union type for all runtime events
RuntimeEvent = Union[
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ActionExecutionStartEvent,
    ActionExecutionArgsEvent,
    ActionExecutionEndEvent,
    ActionExecutionResultEvent,
    AgentStateMessageEvent,
    MetaEvent,
]