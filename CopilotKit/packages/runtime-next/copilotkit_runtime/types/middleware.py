"""
中间件相关类型定义。
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Awaitable, Union
from pydantic import BaseModel, Field

from .messages import Message


class BeforeRequestOptions(BaseModel):
    """请求前选项"""
    thread_id: Optional[str] = Field(None, description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    input_messages: List[Message] = Field(..., description="输入消息")
    properties: Dict[str, Any] = Field(default_factory=dict, description="属性")
    url: Optional[str] = Field(None, description="URL")


class AfterRequestOptions(BaseModel):
    """请求后选项"""
    thread_id: str = Field(..., description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    input_messages: List[Message] = Field(..., description="输入消息")
    output_messages: List[Message] = Field(..., description="输出消息")
    properties: Dict[str, Any] = Field(default_factory=dict, description="属性")
    url: Optional[str] = Field(None, description="URL")


@runtime_checkable
class BeforeRequestHandler(Protocol):
    """请求前处理器协议"""
    
    def __call__(self, options: BeforeRequestOptions) -> Union[None, Awaitable[None]]:
        """处理请求前事件"""
        ...


@runtime_checkable
class AfterRequestHandler(Protocol):
    """请求后处理器协议"""
    
    def __call__(self, options: AfterRequestOptions) -> Union[None, Awaitable[None]]:
        """处理请求后事件"""
        ...


class Middleware(BaseModel):
    """中间件定义"""
    on_before_request: Optional[BeforeRequestHandler] = Field(None, description="请求前处理器", exclude=True)
    on_after_request: Optional[AfterRequestHandler] = Field(None, description="请求后处理器", exclude=True)
    
    class Config:
        arbitrary_types_allowed = True 