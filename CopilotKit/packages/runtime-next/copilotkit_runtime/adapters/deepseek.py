"""
CopilotKit Python 运行时的 DeepSeek 适配器

这是基于 TypeScript 版本实现的完整 DeepSeek 适配器，支持：
- 流式响应处理
- 工具调用和函数执行
- 完整的事件源集成
- DeepSeek 特定的兼容性处理

## 使用示例

```python
import os
from copilotkit_runtime import CopilotRuntime, DeepSeekAdapter
from openai import AsyncOpenAI

# 方式 1: 直接使用 API 密钥
adapter = DeepSeekAdapter(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat"
)

# 方式 2: 使用自定义 OpenAI 客户端
deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
)
adapter = DeepSeekAdapter(openai=deepseek_client)

runtime = CopilotRuntime(adapter=adapter)
```

## 支持的模型

- deepseek-chat (默认): DeepSeek 的旗舰对话模型
- deepseek-coder: 代码专用模型，优化了代码生成和理解能力
- deepseek-reasoner: 推理增强模型，适合复杂问题解决
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
import time
import uuid

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ..types.adapters import CopilotServiceAdapter, AdapterRequest, AdapterResponse
from ..types.messages import (
    Message, 
    TextMessage, 
    ActionExecutionMessage, 
    ResultMessage, 
    MessageRole,
    MessageType
)
from ..types.actions import ActionInput
from ..types.core import ForwardedParameters
from ..events.runtime_events import RuntimeEventSource, RuntimeEvent
from ..utils.common import generate_id


logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_TEMPERATURE_MIN = 0.1
DEEPSEEK_TEMPERATURE_MAX = 2.0


class DeepSeekConfig(BaseModel):
    """DeepSeek 适配器配置"""
    api_key: Optional[str] = Field(None, description="DeepSeek API 密钥")
    model: str = Field(DEFAULT_MODEL, description="模型名称")
    base_url: str = Field(DEEPSEEK_BASE_URL, description="API 基础URL")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: float = Field(0.7, description="温度参数")
    timeout: float = Field(60.0, description="请求超时时间")
    max_retries: int = Field(3, description="最大重试次数")
    disable_parallel_tool_calls: bool = Field(False, description="是否禁用并行工具调用")
    headers: Optional[Dict[str, str]] = Field(None, description="额外请求头")


class EventStream:
    """模拟 TypeScript 版本的 eventStream$"""
    
    def __init__(self, event_source: RuntimeEventSource):
        self.event_source = event_source
        
    async def send_text_message_start(self, data: Dict[str, Any]):
        """发送文本消息开始事件"""
        await self.event_source.emit(RuntimeEvent(
            type="text_message_start",
            data=data
        ))
    
    async def send_text_message_content(self, data: Dict[str, Any]):
        """发送文本消息内容事件"""
        await self.event_source.emit(RuntimeEvent(
            type="text_message_content", 
            data=data
        ))
    
    async def send_text_message_end(self, data: Dict[str, Any]):
        """发送文本消息结束事件"""
        await self.event_source.emit(RuntimeEvent(
            type="text_message_end",
            data=data
        ))
    
    async def send_action_execution_start(self, data: Dict[str, Any]):
        """发送动作执行开始事件"""
        await self.event_source.emit(RuntimeEvent(
            type="action_execution_start",
            data=data
        ))
    
    async def send_action_execution_args(self, data: Dict[str, Any]):
        """发送动作执行参数事件"""
        await self.event_source.emit(RuntimeEvent(
            type="action_execution_args",
            data=data
        ))
    
    async def send_action_execution_end(self, data: Dict[str, Any]):
        """发送动作执行结束事件"""
        await self.event_source.emit(RuntimeEvent(
            type="action_execution_end",
            data=data
        ))
    
    def complete(self):
        """标记流完成"""
        # 在 Python 中这可能不需要特殊处理
        pass


class DeepSeekAdapter(CopilotServiceAdapter):
    """
    DeepSeek API 适配器
    
    实现了与 DeepSeek API 的完整集成，包括流式响应、工具调用等功能。
    """
    
    def __init__(self, openai: Optional[AsyncOpenAI] = None, **kwargs):
        """
        初始化 DeepSeek 适配器
        
        Args:
            openai: 可选的 AsyncOpenAI 客户端实例
            **kwargs: 其他配置参数
        """
        # 如果提供了 openai 客户端，直接使用
        if openai is not None:
            self._openai = openai
            # 从 kwargs 中提取配置，但 api_key 使用客户端的
            config_dict = kwargs.copy()
            if "api_key" not in config_dict:
                config_dict["api_key"] = "provided_via_client"
            self.config = DeepSeekConfig(**config_dict)
        else:
            # 否则根据配置创建客户端
            self.config = DeepSeekConfig(**kwargs)
            if not self.config.api_key:
                raise ValueError("DeepSeek API key is required when openai instance is not provided")
            
            self._openai = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
                default_headers={
                    "User-Agent": "CopilotKit-DeepSeek-Adapter",
                    **(self.config.headers or {})
                }
            )
        
        logger.info(f"🚀 DeepSeekAdapter initialized with model: {self.config.model}")
    
    @property
    def openai(self) -> AsyncOpenAI:
        """获取 OpenAI 客户端"""
        return self._openai
    
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return "deepseek"
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config.model
    
    def get_model(self) -> Optional[str]:
        """获取默认模型名称"""
        return self.config.model
    
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """
        处理聊天完成请求
        
        Args:
            request: 适配器请求
            
        Returns:
            适配器响应
        """
        thread_id = request.thread_id or generate_id()
        model = request.model or self.config.model
        messages = request.messages
        actions = request.actions or []
        event_source = request.event_source
        forwarded_parameters = request.forwarded_parameters or ForwardedParameters()
        
        logger.info(f"🔄 [DeepSeek] Processing request: thread_id={thread_id}, model={model}, "
                   f"messages_count={len(messages)}, actions_count={len(actions)}")
        
        # 转换动作为 OpenAI 工具格式
        tools = [self._convert_action_to_openai_tool(action) for action in actions]
        
        # 过滤和处理消息（实现 TypeScript 版本的 ALLOWLIST 逻辑）
        filtered_messages = self._filter_messages_with_allowlist(messages)
        
        # 转换消息为 OpenAI 格式
        openai_messages = [
            self._convert_message_to_openai(msg) for msg in filtered_messages
        ]
        
        # DeepSeek 兼容性修复：将 'developer' 角色转换为 'system'
        openai_messages = self._fix_deepseek_compatibility(openai_messages)
        
        # 构建请求参数
        request_payload = self._build_request_payload(
            model=model,
            messages=openai_messages,
            tools=tools,
            forwarded_parameters=forwarded_parameters
        )
        
        logger.debug(f"📤 [DeepSeek] API Request payload: {json.dumps(request_payload, indent=2)}")
        
        try:
            # 创建流式请求
            stream = await self._openai.chat.completions.create(**request_payload)
            
            logger.info("🔄 [DeepSeek] Stream created successfully, starting to process...")
            
            # 如果有事件源，处理流式响应
            if event_source:
                await self._process_streaming_response(
                    stream=stream,
                    event_source=event_source,
                    thread_id=thread_id,
                    actions=actions
                )
            
            return AdapterResponse(
                thread_id=thread_id,
                event_source=event_source
            )
            
        except Exception as error:
            logger.error(f"❌ [DeepSeek] API error: {error}")
            
            # 如果有事件源，发送错误事件
            if event_source:
                await event_source.emit(RuntimeEvent(
                    type="error",
                    data={
                        "error": str(error),
                        "provider": "deepseek",
                        "threadId": thread_id
                    }
                ))
            
            raise Exception(f"DeepSeek API request failed: {error}")
    
    def _filter_messages_with_allowlist(self, messages: List[Message]) -> List[Message]:
        """
        使用 ALLOWLIST 方法过滤消息（复制 TypeScript 版本的逻辑）
        
        只包含对应有效 tool_call 的 tool_result 消息
        """
        # 步骤 1: 提取有效的 tool_call ID
        valid_tool_use_ids: Set[str] = set()
        
        for message in messages:
            if message.is_action_execution_message():
                valid_tool_use_ids.add(message.id)
        
        # 步骤 2: 过滤消息，只保留有效 tool_call ID 的消息
        filtered_messages = []
        
        for message in messages:
            if message.is_result_message():
                # 如果没有对应的 tool_call，跳过
                if message.action_execution_id not in valid_tool_use_ids:
                    continue
                
                # 从有效 ID 中移除，避免处理重复
                valid_tool_use_ids.discard(message.action_execution_id)
                filtered_messages.append(message)
            else:
                # 保留所有非工具结果消息
                filtered_messages.append(message)
        
        return filtered_messages
    
    def _convert_message_to_openai(self, message: Message) -> Dict[str, Any]:
        """将 CopilotKit 消息转换为 OpenAI 格式"""
        if isinstance(message, TextMessage):
            return {
                "role": message.role.value,
                "content": message.content
            }
        elif isinstance(message, ActionExecutionMessage):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": message.id,
                    "type": "function",
                    "function": {
                        "name": message.name,
                        "arguments": json.dumps(message.arguments)
                    }
                }]
            }
        elif isinstance(message, ResultMessage):
            return {
                "role": "tool",
                "tool_call_id": message.action_execution_id,
                "content": json.dumps(message.result) if not isinstance(message.result, str) else message.result
            }
        else:
            # 默认处理
            return {
                "role": "user",
                "content": str(message)
            }
    
    def _fix_deepseek_compatibility(self, openai_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        DeepSeek 兼容性修复：将不支持的 'developer' 角色转换为 'system'
        """
        fixed_messages = []
        
        for message in openai_messages:
            if message and isinstance(message, dict) and message.get('role') == 'developer':
                logger.debug('🔄 [DeepSeek] Converting developer role to system role')
                fixed_message = message.copy()
                fixed_message['role'] = 'system'
                fixed_messages.append(fixed_message)
            else:
                fixed_messages.append(message)
        
        return fixed_messages
    
    def _convert_action_to_openai_tool(self, action: ActionInput) -> Dict[str, Any]:
        """将 CopilotKit 动作转换为 OpenAI 工具格式"""
        properties = {}
        required = []
        
        for param in action.parameters:
            properties[param.name] = {
                "type": param.type.value if hasattr(param.type, 'value') else str(param.type),
                "description": param.description
            }
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": action.name,
                "description": action.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def _build_request_payload(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        forwarded_parameters: ForwardedParameters
    ) -> Dict[str, Any]:
        """构建 DeepSeek API 请求负载"""
        payload = {
            "model": model,
            "stream": True,
            "messages": messages,
        }
        
        # 添加工具
        if tools:
            payload["tools"] = tools
            
            # 处理工具选择
            tool_choice = forwarded_parameters.tool_choice
            if tool_choice == "function" and forwarded_parameters.tool_choice_function_name:
                payload["tool_choice"] = {
                    "type": "function",
                    "function": {"name": forwarded_parameters.tool_choice_function_name}
                }
            elif tool_choice:
                payload["tool_choice"] = tool_choice
            
            # 处理并行工具调用
            if self.config.disable_parallel_tool_calls:
                payload["parallel_tool_calls"] = False
        
        # 添加其他参数
        if forwarded_parameters.max_tokens:
            payload["max_tokens"] = forwarded_parameters.max_tokens
        
        if forwarded_parameters.stop:
            payload["stop"] = forwarded_parameters.stop
        
        if forwarded_parameters.temperature is not None:
            # DeepSeek 温度范围限制
            temperature = max(
                DEEPSEEK_TEMPERATURE_MIN,
                min(DEEPSEEK_TEMPERATURE_MAX, forwarded_parameters.temperature)
            )
            payload["temperature"] = temperature
        
        return payload
    
    async def _process_streaming_response(
        self,
        stream,
        event_source: RuntimeEventSource,
        thread_id: str,
        actions: List[ActionInput]
    ):
        """处理流式响应（复制 TypeScript 版本的完整逻辑）"""
        
        async def stream_callback(event_stream_iter):
            event_stream = EventStream(event_source)
            
            mode: Optional[str] = None  # "function" | "message" | None
            current_message_id: str = ""
            current_tool_call_id: str = ""
            current_action_name: str = ""
            
            try:
                logger.info("🔄 [DeepSeek] Starting stream iteration...")
                chunk_count = 0
                
                async for chunk in stream:
                    chunk_count += 1
                    
                    logger.debug(f"📦 [DeepSeek] Received chunk #{chunk_count}: "
                               f"choices_length={len(chunk.choices)}, "
                               f"finish_reason={chunk.choices[0].finish_reason if chunk.choices else None}")
                    
                    if not chunk.choices:
                        continue
                    
                    choice = chunk.choices[0]
                    tool_call = choice.delta.tool_calls[0] if choice.delta.tool_calls else None
                    content = choice.delta.content
                    finish_reason = choice.finish_reason
                    
                    # 检查是否应该结束流
                    if finish_reason:
                        logger.info(f"🏁 [DeepSeek] Finish reason detected: {finish_reason}")
                    
                    # 模式切换逻辑（来自 TypeScript 版本）
                    # 从消息模式切换到函数模式
                    if mode == "message" and tool_call and tool_call.id:
                        logger.debug("🔧 [DeepSeek] Switching from message to function mode")
                        mode = None
                        await event_stream.send_text_message_end({"messageId": current_message_id})
                    
                    # 从函数模式切换到消息模式或新函数
                    elif mode == "function" and (not tool_call or tool_call.id):
                        logger.debug("🔧 [DeepSeek] Switching from function to message/new function mode")
                        mode = None
                        await event_stream.send_action_execution_end({"actionExecutionId": current_tool_call_id})
                    
                    # 开始新的模式
                    if mode is None:
                        if tool_call and tool_call.id:
                            logger.debug("🚀 [DeepSeek] Starting function mode")
                            mode = "function"
                            current_tool_call_id = tool_call.id
                            current_action_name = tool_call.function.name if tool_call.function else ""
                            
                            await event_stream.send_action_execution_start({
                                "actionExecutionId": current_tool_call_id,
                                "parentMessageId": chunk.id,
                                "actionName": current_action_name
                            })
                        
                        elif content:
                            logger.debug("💬 [DeepSeek] Starting message mode")
                            mode = "message"
                            current_message_id = chunk.id or generate_id()
                            await event_stream.send_text_message_start({"messageId": current_message_id})
                    
                    # 发送内容事件
                    if mode == "message" and content:
                        logger.debug(f"💬 [DeepSeek] Sending text content: {content}")
                        await event_stream.send_text_message_content({
                            "messageId": current_message_id,
                            "content": content
                        })
                    
                    elif mode == "function" and tool_call and tool_call.function and tool_call.function.arguments:
                        logger.debug(f"📝 [DeepSeek] Sending function arguments: {tool_call.function.arguments}")
                        await event_stream.send_action_execution_args({
                            "actionExecutionId": current_tool_call_id,
                            "args": tool_call.function.arguments
                        })
                    
                    # 如果有结束原因，跳出循环
                    if finish_reason:
                        logger.debug(f"🔚 [DeepSeek] Breaking loop due to finish reason: {finish_reason}")
                        break
                
                # 发送最终结束事件
                logger.info(f"🏁 [DeepSeek] Stream loop ended after {chunk_count} chunks, sending final events")
                
                if mode == "message":
                    logger.debug("💬 [DeepSeek] Ending final text message")
                    await event_stream.send_text_message_end({"messageId": current_message_id})
                elif mode == "function":
                    logger.debug("🔧 [DeepSeek] Ending final function execution")
                    await event_stream.send_action_execution_end({"actionExecutionId": current_tool_call_id})
                
            except Exception as error:
                logger.error(f"❌ [DeepSeek] Streaming error: {error}")
                
                # 错误清理
                if mode == "message":
                    logger.debug("💬 [DeepSeek] Error cleanup: ending text message")
                    await event_stream.send_text_message_end({"messageId": current_message_id})
                elif mode == "function" and current_tool_call_id:
                    logger.debug("🔧 [DeepSeek] Error cleanup: ending function execution")
                    await event_stream.send_action_execution_end({"actionExecutionId": current_tool_call_id})
                
                raise error
            
            # 完成事件流
            logger.info("🎉 [DeepSeek] Completing event stream")
            event_stream.complete()
        
        # 启动流处理
        event_source.stream(stream_callback)


# 便捷函数
def create_deepseek_adapter(
    api_key: str,
    model: str = DEFAULT_MODEL,
    **kwargs
) -> DeepSeekAdapter:
    """
    创建 DeepSeek 适配器的便捷函数
    
    Args:
        api_key: DeepSeek API 密钥
        model: 模型名称
        **kwargs: 其他配置参数
        
    Returns:
        DeepSeek 适配器实例
    """
    return DeepSeekAdapter(
        api_key=api_key,
        model=model,
        **kwargs
    ) 