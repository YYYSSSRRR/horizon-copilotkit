"""
运行时类型定义。
"""

from typing import Any, Dict, List, Optional, Union, Callable
from pydantic import Field

from .core import BaseType
from .messages import Message
from .actions import Action, ActionInput
from .agents import Agent


class RequestContext(BaseType):
    """请求上下文"""
    properties: Dict[str, Any] = Field(default_factory=dict, description="上下文属性")
    url: Optional[str] = Field(None, description="请求URL")


class AgentSession(BaseType):
    """代理会话"""
    agent_name: str = Field(..., description="代理名称")
    thread_id: Optional[str] = Field(None, description="线程ID")
    node_name: Optional[str] = Field(None, description="节点名称")


class CopilotRuntimeRequest(BaseType):
    """
    CopilotRuntime请求对象
    
    包含处理请求所需的所有信息。
    """
    service_adapter: Any = Field(..., description="服务适配器")
    messages: List[Message] = Field(..., description="输入消息列表")
    actions: Optional[List[Action]] = Field(None, description="可用动作列表")
    thread_id: Optional[str] = Field(None, description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    context: Optional[RequestContext] = Field(None, description="请求上下文")
    agent_session: Optional[AgentSession] = Field(None, description="代理会话")


class CopilotRuntimeResponse(BaseType):
    """
    CopilotRuntime响应对象
    
    包含处理结果和事件源。
    """
    thread_id: str = Field(..., description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    event_source: Any = Field(..., description="事件源")
    server_side_actions: List[Action] = Field(default_factory=list, description="服务器端动作")
    action_inputs_without_agents: List[ActionInput] = Field(default_factory=list, description="非代理动作输入列表")


# 定义中间件类型
ActionsConfiguration = Union[
    List[Action],
    Callable[[Dict[str, Any]], List[Action]]
]

OnBeforeRequestHandler = Callable[[Dict[str, Any]], Optional[Any]]
OnAfterRequestHandler = Callable[[Dict[str, Any]], Optional[Any]]


class Middleware(BaseType):
    """中间件配置"""
    on_before_request: Optional[OnBeforeRequestHandler] = Field(None, description="请求前处理器")
    on_after_request: Optional[OnAfterRequestHandler] = Field(None, description="请求后处理器") 