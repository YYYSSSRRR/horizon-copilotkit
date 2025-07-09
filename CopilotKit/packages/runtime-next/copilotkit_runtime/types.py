"""
基础类型定义

这个模块包含了 CopilotKit Runtime 中使用的所有基础类型，
与 react-core-next 的类型保持一致，确保完美兼容。
"""

from typing import Any, Dict, List, Optional, Union, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    ACTION_EXECUTION = "action_execution"
    RESULT = "result" 
    AGENT_STATE = "agent_state"
    IMAGE = "image"


class MessageStatus(BaseModel):
    """消息状态"""
    code: Literal["success", "error", "pending"] = "success"
    reason: Optional[str] = None


class BaseMessage(BaseModel):
    """基础消息类型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: MessageStatus = Field(default_factory=MessageStatus)
    
    class Config:
        use_enum_values = True


class TextMessage(BaseMessage):
    """文本消息"""
    type: Literal[MessageType.TEXT] = MessageType.TEXT
    role: MessageRole
    content: str
    parent_message_id: Optional[str] = None


class ActionExecutionMessage(BaseMessage):
    """动作执行消息"""
    type: Literal[MessageType.ACTION_EXECUTION] = MessageType.ACTION_EXECUTION
    name: str
    arguments: Dict[str, Any]
    parent_message_id: Optional[str] = None


class ResultMessage(BaseMessage):
    """结果消息"""
    type: Literal[MessageType.RESULT] = MessageType.RESULT
    action_execution_id: str
    action_name: str
    result: Any


class AgentStateMessage(BaseMessage):
    """代理状态消息"""
    type: Literal[MessageType.AGENT_STATE] = MessageType.AGENT_STATE
    agent_name: str
    state: Any
    running: bool
    thread_id: str
    node_name: Optional[str] = None
    run_id: Optional[str] = None
    active: bool
    role: MessageRole = MessageRole.ASSISTANT


class ImageMessage(BaseMessage):
    """图像消息"""
    type: Literal[MessageType.IMAGE] = MessageType.IMAGE
    format: str
    bytes: str
    role: MessageRole
    parent_message_id: Optional[str] = None


# 消息联合类型
Message = Union[TextMessage, ActionExecutionMessage, ResultMessage, AgentStateMessage, ImageMessage]


class ActionParameter(BaseModel):
    """动作参数定义"""
    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None


class Action(BaseModel):
    """动作定义"""
    name: str
    description: str
    parameters: List[ActionParameter] = Field(default_factory=list)
    handler: Optional[Any] = None  # 实际的处理函数
    
    class Config:
        arbitrary_types_allowed = True


class AgentSession(BaseModel):
    """代理会话"""
    agent_name: str
    thread_id: str
    status: Literal["running", "waiting", "completed", "failed"]
    metadata: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    """代理状态"""
    agent_name: str
    state: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None


class ForwardedParameters(BaseModel):
    """转发参数"""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


class Extensions(BaseModel):
    """扩展配置"""
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取扩展数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置扩展数据"""
        self.data[key] = value


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Dict[str, Any]]
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_session: Optional[AgentSession] = None
    agent_states: List[AgentState] = Field(default_factory=list)
    forwarded_parameters: Optional[ForwardedParameters] = None
    extensions: Optional[Extensions] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    thread_id: str
    run_id: Optional[str] = None
    extensions: Optional[Extensions] = None
    messages: List[Message] = Field(default_factory=list)


class StreamingChunk(BaseModel):
    """流式响应块"""
    type: Literal["text", "action", "agent_state", "metadata", "error"]
    data: Any
    
    class Config:
        use_enum_values = True


class StreamingResponse(BaseModel):
    """流式响应"""
    thread_id: str
    run_id: Optional[str] = None
    chunks: List[StreamingChunk] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    """运行时配置"""
    debug: bool = False
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    max_message_length: int = 10000
    timeout: int = 30
    stream_timeout: int = 60


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# 便捷的工厂函数
def create_text_message(
    content: str, 
    role: MessageRole = MessageRole.ASSISTANT,
    message_id: Optional[str] = None,
    parent_message_id: Optional[str] = None
) -> TextMessage:
    """创建文本消息"""
    return TextMessage(
        id=message_id or str(uuid.uuid4()),
        role=role,
        content=content,
        parent_message_id=parent_message_id
    )


def create_action_message(
    name: str,
    arguments: Dict[str, Any],
    message_id: Optional[str] = None,
    parent_message_id: Optional[str] = None
) -> ActionExecutionMessage:
    """创建动作执行消息"""
    return ActionExecutionMessage(
        id=message_id or str(uuid.uuid4()),
        name=name,
        arguments=arguments,
        parent_message_id=parent_message_id
    )


def create_result_message(
    action_execution_id: str,
    action_name: str,
    result: Any,
    message_id: Optional[str] = None
) -> ResultMessage:
    """创建结果消息"""
    return ResultMessage(
        id=message_id or str(uuid.uuid4()),
        action_execution_id=action_execution_id,
        action_name=action_name,
        result=result
    )


def create_agent_state_message(
    agent_name: str,
    state: Any,
    running: bool,
    thread_id: str,
    active: bool,
    message_id: Optional[str] = None,
    node_name: Optional[str] = None,
    run_id: Optional[str] = None
) -> AgentStateMessage:
    """创建代理状态消息"""
    return AgentStateMessage(
        id=message_id or str(uuid.uuid4()),
        agent_name=agent_name,
        state=state,
        running=running,
        thread_id=thread_id,
        active=active,
        node_name=node_name,
        run_id=run_id
    ) 