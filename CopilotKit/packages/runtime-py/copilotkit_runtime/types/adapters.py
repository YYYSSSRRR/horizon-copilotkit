"""
适配器类型定义

对标TypeScript runtime中的适配器系统
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .messages import Message
from .actions import ActionInput


class AdapterRequest(BaseModel):
    """适配器请求"""
    messages: List[Message] = Field(..., description="消息列表")
    actions: List[ActionInput] = Field(default_factory=list, description="可用动作列表")
    model: Optional[str] = Field(None, description="模型名称")
    thread_id: Optional[str] = Field(None, description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    forwarded_parameters: Optional[Dict[str, Any]] = Field(None, description="转发参数")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


class AdapterResponse(BaseModel):
    """适配器响应"""
    message: Optional[Message] = Field(None, description="响应消息")
    messages: Optional[List[Message]] = Field(None, description="响应消息列表")
    thread_id: Optional[str] = Field(None, description="线程ID")
    run_id: Optional[str] = Field(None, description="运行ID")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


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
    """空适配器实现"""
    
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """处理请求（空实现）"""
        return AdapterResponse() 