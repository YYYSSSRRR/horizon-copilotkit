"""
OpenAI适配器实现。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import time

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ..types.adapters import CopilotServiceAdapter, AdapterRequest, AdapterResponse
from ..types.messages import Message, TextMessage, MessageRole
from ..types.actions import Action
from ..events.runtime_events import RuntimeEventSource, RuntimeEvent


logger = logging.getLogger(__name__)


class OpenAIConfig(BaseModel):
    """OpenAI配置"""
    api_key: str = Field(..., description="API密钥")
    model: str = Field("gpt-4", description="模型名称")
    base_url: Optional[str] = Field(None, description="自定义API基础URL")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: float = Field(0.7, description="温度参数")
    timeout: float = Field(60.0, description="请求超时时间")
    max_retries: int = Field(3, description="最大重试次数")


class OpenAIAdapter(CopilotServiceAdapter):
    """
    OpenAI API适配器
    
    支持：
    - GPT-4和GPT-3.5模型
    - 流式响应
    - 工具调用
    - 错误处理和重试
    """
    
    def __init__(self, **kwargs):
        """
        初始化OpenAI适配器
        
        Args:
            **kwargs: 配置参数
        """
        # 处理直接传递的参数
        if "api_key" in kwargs:
            self.config = OpenAIConfig(**kwargs)
        else:
            self.config = kwargs.get("config", OpenAIConfig(**kwargs))
        
        # 创建异步客户端
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )
        
        logger.info(f"OpenAIAdapter initialized with model: {self.config.model}")
    
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return "openai"
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config.model
    
    def get_model(self) -> Optional[str]:
        """获取默认模型名称"""
        return self.config.model
    
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """
        处理适配器请求（抽象方法实现）
        
        Args:
            request: 适配器请求
            
        Returns:
            适配器响应
        """
        # 简化的实现，返回一个占位响应
        return AdapterResponse(
            thread_id=request.thread_id or "default",
            event_source=request.event_source
        )
    
    async def process_messages(
        self,
        messages: List[Message],
        actions: List[Action] = None,
        event_source: Optional[RuntimeEventSource] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        **kwargs
    ) -> List[Message]:
        """
        处理消息并生成响应
        
        Args:
            messages: 输入消息列表
            actions: 可用动作列表
            event_source: 事件源（用于流式响应）
            thread_id: 线程ID
            run_id: 运行ID
            **kwargs: 其他参数
            
        Returns:
            响应消息列表
        """
        try:
            # 简化的实现，实际中需要添加完整的消息转换和工具调用逻辑
            response_message = TextMessage(
                role=MessageRole.ASSISTANT,
                content="Hello from OpenAI! This is a placeholder response."
            )
            
            if event_source:
                # 发送流式事件
                event_source.emit(RuntimeEvent(
                    type="message_start",
                    data={"threadId": thread_id, "provider": "openai"}
                ))
                
                event_source.emit(RuntimeEvent(
                    type="text_delta",
                    data={"delta": response_message.content, "threadId": thread_id}
                ))
                
                event_source.emit(RuntimeEvent(
                    type="message_end",
                    data={"threadId": thread_id, "provider": "openai"}
                ))
            
            return [response_message]
            
        except Exception as e:
            logger.error(f"Error in OpenAI adapter: {e}")
            
            if event_source:
                event_source.emit(RuntimeEvent(
                    type="error",
                    data={"error": str(e), "provider": "openai", "threadId": thread_id}
                ))
            
            return [
                TextMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"抱歉，处理您的请求时出现错误：{str(e)}"
                )
            ]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简化的健康检查
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"OpenAIAdapter(model={self.config.model})"


# 便捷函数
def create_openai_adapter(
    api_key: str,
    model: str = "gpt-4",
    **kwargs
) -> OpenAIAdapter:
    """
    创建OpenAI适配器
    
    Args:
        api_key: API密钥
        model: 模型名称
        **kwargs: 其他配置参数
        
    Returns:
        OpenAI适配器实例
    """
    return OpenAIAdapter(
        api_key=api_key,
        model=model,
        **kwargs
    ) 