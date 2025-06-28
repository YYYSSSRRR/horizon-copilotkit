"""
CopilotKit Python 运行时核心类型定义

本模块定义了运行时中使用的所有核心类型，保持与 TypeScript 版本的兼容性。

包含的主要类型：
- 消息类型：文本消息、Action 执行消息、结果消息、代理状态消息、图片消息
- Action 和参数定义
- 请求和响应类型
- 中间件和可观测性配置
- GraphQL 输入/输出类型
- 事件和扩展类型

所有类型都使用 Pydantic 进行数据验证，使用 Strawberry GraphQL 进行 API 定义。
"""

from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Callable,
    Awaitable,
    Protocol,
    TypeVar,
    Generic,
)
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import strawberry
from strawberry.scalars import JSON

T = TypeVar("T")


@strawberry.enum
class MessageRole(Enum):
    """消息角色枚举
    
    定义聊天中不同参与者的角色：
    - SYSTEM: 系统消息，用于设置 AI 行为和上下文
    - USER: 用户消息，来自最终用户的输入
    - ASSISTANT: 助手消息，AI 的回复
    - FUNCTION: 函数消息，工具调用的结果
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@strawberry.enum
class ActionInputAvailability(Enum):
    """Action 输入可用性枚举
    
    控制 Action 是否可用：
    - AVAILABLE: 可用状态，可以被调用
    - DISABLED: 禁用状态，不可被调用
    """
    AVAILABLE = "available"
    DISABLED = "disabled"


class Parameter(BaseModel):
    """Action 参数定义
    
    定义 Action 函数的参数规范：
    - name: 参数名称
    - type: 参数类型（string, number, boolean, array, object）
    - description: 参数描述，帮助 AI 理解参数用途
    - required: 是否为必需参数
    - enum: 枚举值列表，限制参数可选值
    """
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    enum: Optional[List[str]] = None


class Action(BaseModel, Generic[T]):
    """Action（工具）定义
    
    定义可供 AI 调用的工具函数：
    - name: Action 名称，AI 用于识别和调用
    - description: Action 描述，帮助 AI 理解功能
    - parameters: 参数列表，定义函数签名
    - handler: 处理函数，实际执行逻辑
    
    示例:
        weather_action = Action(
            name="get_weather",
            description="获取指定城市的天气信息",
            parameters=[
                Parameter(name="city", type="string", required=True)
            ],
            handler=get_weather_handler
        )
    """
    name: str
    description: Optional[str] = None
    parameters: Optional[List[Parameter]] = None
    handler: Optional[Callable[..., Any]] = None
    
    class Config:
        arbitrary_types_allowed = True


# 消息类型定义
@strawberry.type
class TextMessage:
    """文本消息类型
    
    表示普通的文本聊天消息：
    - content: 消息内容
    - parent_message_id: 父消息 ID，用于消息链追踪
    - role: 消息角色（用户、助手、系统等）
    """
    content: str
    parent_message_id: Optional[str] = None
    role: MessageRole


@strawberry.type  
class ActionExecutionMessage:
    """Action 执行消息类型
    
    表示 AI 要执行的工具调用：
    - name: 要执行的 Action 名称
    - arguments: JSON 格式的参数字符串
    - parent_message_id: 父消息 ID
    - scope: 执行范围（可选）
    """
    name: str
    arguments: str
    parent_message_id: Optional[str] = None
    scope: Optional[str] = None


@strawberry.type
class ResultMessage:
    """结果消息类型
    
    表示 Action 执行的结果：
    - action_execution_id: 对应的 Action 执行 ID
    - action_name: Action 名称
    - parent_message_id: 父消息 ID
    - result: 执行结果（通常为 JSON 字符串）
    """
    action_execution_id: str
    action_name: str
    parent_message_id: Optional[str] = None
    result: str


@strawberry.type
class AgentStateMessage:
    """代理状态消息类型
    
    表示 AI 代理的内部状态信息：
    - thread_id: 会话线程 ID
    - agent_name: 代理名称
    - role: 消息角色
    - state: 代理状态数据
    - running: 是否正在运行
    - node_name: 当前节点名称
    - run_id: 运行 ID
    - active: 是否活跃
    """
    thread_id: str
    agent_name: str
    role: MessageRole
    state: str
    running: bool
    node_name: str
    run_id: str
    active: bool


@strawberry.type
class ImageMessage:
    """图片消息类型
    
    表示图片消息：
    - format: 图片格式（如 "png", "jpeg"）
    - bytes: Base64 编码的图片数据
    - parent_message_id: 父消息 ID
    - role: 消息角色
    """
    format: str
    bytes: str
    parent_message_id: Optional[str] = None
    role: MessageRole


@strawberry.type
class Message:
    """Main message type"""
    id: str
    created_at: datetime
    text_message: Optional[TextMessage] = None
    action_execution_message: Optional[ActionExecutionMessage] = None
    result_message: Optional[ResultMessage] = None
    agent_state_message: Optional[AgentStateMessage] = None
    image_message: Optional[ImageMessage] = None


# Input types for GraphQL
@strawberry.input
class TextMessageInput:
    """Text message input type"""
    content: str
    parent_message_id: Optional[str] = None
    role: MessageRole


@strawberry.input
class ActionExecutionMessageInput:
    """Action execution message input type"""
    name: str
    arguments: str
    parent_message_id: Optional[str] = None
    scope: Optional[str] = None


@strawberry.input
class ResultMessageInput:
    """Result message input type"""
    action_execution_id: str
    action_name: str
    parent_message_id: Optional[str] = None
    result: str


@strawberry.input
class AgentStateMessageInput:
    """Agent state message input type"""
    thread_id: str
    agent_name: str
    role: MessageRole
    state: str
    running: bool
    node_name: str
    run_id: str
    active: bool


@strawberry.input
class ImageMessageInput:
    """Image message input type"""
    format: str
    bytes: str
    parent_message_id: Optional[str] = None
    role: MessageRole


@strawberry.input
class MessageInput:
    """Main message input type"""
    id: str
    created_at: datetime
    text_message: Optional[TextMessageInput] = None
    action_execution_message: Optional[ActionExecutionMessageInput] = None
    result_message: Optional[ResultMessageInput] = None
    agent_state_message: Optional[AgentStateMessageInput] = None
    image_message: Optional[ImageMessageInput] = None


@strawberry.input
class ActionInput:
    """Action input type"""
    name: str
    description: Optional[str] = None
    json_schema: Optional[JSON] = None
    availability: ActionInputAvailability = ActionInputAvailability.AVAILABLE


@strawberry.input
class ForwardedParametersInput:
    """Forwarded parameters input type"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


@strawberry.input
class AgentSessionInput:
    """Agent session input type"""
    agent_name: str
    thread_id: Optional[str] = None


@strawberry.input
class AgentStateInput:
    """Agent state input type"""
    agent_name: str
    state: str
    thread_id: str
    run_id: str
    node_name: str
    active: bool


@strawberry.input
class ExtensionsInput:
    """Extensions input type"""
    data: Optional[JSON] = None


@strawberry.input
class MetaEventInput:
    """Meta event input type"""
    event_type: str
    data: Optional[JSON] = None


# Response types
@strawberry.type
class ExtensionsResponse:
    """Extensions response type"""
    data: Optional[JSON] = None


@strawberry.type
class LoadAgentStateResponse:
    """Load agent state response type"""
    state: Optional[str] = None
    thread_id: str
    run_id: Optional[str] = None


@strawberry.type
class Agent:
    """Agent type"""
    name: str
    description: str


# Runtime types
class OnBeforeRequestOptions(BaseModel):
    """Options for before request handler"""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    input_messages: List[Message]
    properties: Dict[str, Any]
    url: Optional[str] = None


class OnAfterRequestOptions(BaseModel):
    """Options for after request handler"""
    thread_id: str
    run_id: Optional[str] = None
    input_messages: List[Message]
    output_messages: List[Message]
    properties: Dict[str, Any]
    url: Optional[str] = None


OnBeforeRequestHandler = Callable[[OnBeforeRequestOptions], Union[None, Awaitable[None]]]
OnAfterRequestHandler = Callable[[OnAfterRequestOptions], Union[None, Awaitable[None]]]


class Middleware(BaseModel):
    """Middleware configuration"""
    on_before_request: Optional[OnBeforeRequestHandler] = None
    on_after_request: Optional[OnAfterRequestHandler] = None
    
    class Config:
        arbitrary_types_allowed = True


ActionsConfiguration = Union[
    List[Action[Any]],
    Callable[[Dict[str, Any]], List[Action[Any]]]
]


class GraphQLContext(BaseModel):
    """GraphQL context"""
    headers: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)


class CopilotRuntimeRequest(BaseModel):
    """Runtime request type"""
    service_adapter: Any  # CopilotServiceAdapter
    messages: List[MessageInput]
    actions: List[ActionInput]
    agent_session: Optional[AgentSessionInput] = None
    agent_states: Optional[List[AgentStateInput]] = None
    output_messages_promise: Any  # Future[List[Message]]
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    public_api_key: Optional[str] = None
    graphql_context: GraphQLContext
    forwarded_parameters: Optional[ForwardedParametersInput] = None
    url: Optional[str] = None
    extensions: Optional[ExtensionsInput] = None
    meta_events: Optional[List[MetaEventInput]] = None
    
    class Config:
        arbitrary_types_allowed = True


class CopilotRuntimeResponse(BaseModel):
    """Runtime response type"""
    thread_id: str
    run_id: Optional[str] = None
    event_source: Any  # RuntimeEventSource
    server_side_actions: List[Action[Any]]
    action_inputs_without_agents: List[ActionInput]
    extensions: Optional[ExtensionsResponse] = None
    
    class Config:
        arbitrary_types_allowed = True


# Observability types
class LLMRequestData(BaseModel):
    """LLM request data for logging"""
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class LLMResponseData(BaseModel):
    """LLM response data for logging"""
    content: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class LLMErrorData(BaseModel):
    """LLM error data for logging"""
    error_type: str
    error_message: str
    error_code: Optional[str] = None


class Logger(Protocol):
    """Logger protocol for observability"""
    
    def log_request(self, data: LLMRequestData) -> None:
        """Log LLM request"""
        ...
    
    def log_response(self, data: LLMResponseData) -> None:
        """Log LLM response"""
        ...
    
    def log_error(self, data: LLMErrorData) -> None:
        """Log LLM error"""
        ...


class CopilotObservabilityConfig(BaseModel):
    """Observability configuration"""
    enabled: bool = False
    progressive: bool = True
    logger: Optional[Logger] = None
    
    class Config:
        arbitrary_types_allowed = True 