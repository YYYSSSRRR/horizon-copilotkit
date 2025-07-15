"""
适配器相关类型定义。
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

from .messages import Message
from .actions import ActionInput
from .core import ForwardedParameters


@runtime_checkable
class EventSource(Protocol):
    """事件源协议"""
    
    def stream(self, callback) -> None:
        """流式处理事件"""
        ...


class AdapterRequest(BaseModel):
    """适配器请求"""
    thread_id: Optional[str] = Field(None, description="线程ID")
    model: Optional[str] = Field(None, description="模型名称")
    messages: List[Message] = Field(..., description="消息列表")
    actions: List[ActionInput] = Field(default_factory=list, description="可用动作列表")
    event_source: Optional[EventSource] = Field(None, description="事件源", exclude=True)
    forwarded_parameters: Optional[ForwardedParameters] = Field(None, description="转发参数")
    
    class Config:
        arbitrary_types_allowed = True


class AdapterResponse(BaseModel):
    """适配器响应"""
    thread_id: str = Field(..., description="线程ID")
    event_source: EventSource = Field(..., description="事件源", exclude=True)
    
    class Config:
        arbitrary_types_allowed = True


class CopilotServiceAdapter(ABC):
    """CopilotKit服务适配器抽象基类"""
    
    @abstractmethod
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """
        处理聊天完成请求
        
        Args:
            request: 适配器请求
            
        Returns:
            适配器响应
        """
        pass
    
    def get_model(self) -> Optional[str]:
        """获取默认模型名称"""
        return None
    
    def supports_streaming(self) -> bool:
        """是否支持流式响应"""
        return True
    
    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        return True 


class EmptyAdapter(CopilotServiceAdapter):
    """空适配器，用于agent lock模式"""
    
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """
        空适配器不处理请求，抛出错误
        """
        raise RuntimeError("EmptyAdapter不应该被用于处理请求。这个适配器只用于agent lock模式。")
    
    def supports_streaming(self) -> bool:
        return False
    
    def supports_function_calling(self) -> bool:
        return False