"""
运行时类型定义

对标TypeScript runtime中的运行时相关类型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .messages import Message
from .actions import ActionInput
from .status import BaseMessageStatus


class CopilotRuntimeRequest(BaseModel):
    """Copilot运行时请求"""
    messages: List[Message] = Field(..., description="消息列表")
    actions: List[ActionInput] = Field(default_factory=list, description="可用动作")
    thread_id: Optional[str] = Field(None, description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    public_api_key: Optional[str] = Field(None, description="公共API密钥")
    forwarded_parameters: Optional[Dict[str, Any]] = Field(None, description="转发参数")
    url: Optional[str] = Field(None, description="请求URL")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展信息")
    agent_session: Optional[Dict[str, Any]] = Field(None, description="代理会话")
    agent_states: Optional[List[Dict[str, Any]]] = Field(None, description="代理状态")


class CopilotResponse(BaseModel):
    """Copilot响应"""
    thread_id: str = Field(..., description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    messages: List[Message] = Field(..., description="响应消息列表")
    status: BaseMessageStatus = Field(..., description="响应状态")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展响应")
    meta_events: Optional[List[Dict[str, Any]]] = Field(None, description="元事件") 