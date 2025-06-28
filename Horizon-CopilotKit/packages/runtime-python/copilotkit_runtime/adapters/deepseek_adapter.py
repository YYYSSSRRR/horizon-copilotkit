"""
CopilotKit 运行时的 DeepSeek 适配器

DeepSeek 是一家专注于 AI 研究的公司，提供强大的大语言模型服务。
本适配器为 CopilotKit 提供对 DeepSeek AI 模型的完整支持。

## 使用示例

```python
from copilotkit_runtime import CopilotRuntime, DeepSeekAdapter
from openai import AsyncOpenAI

# 创建运行时实例
copilot_kit = CopilotRuntime()

# 方法 1: 直接使用 API Key
adapter = DeepSeekAdapter(
    api_key="your-deepseek-api-key",
    model="deepseek-chat"
)

# 方法 2: 使用预配置的 OpenAI 客户端
deepseek = AsyncOpenAI(
    api_key="your-deepseek-api-key",
    base_url="https://api.deepseek.com/v1",
)
adapter = DeepSeekAdapter(openai=deepseek)
```

## 支持的模型

DeepSeek 支持以下模型：
- deepseek-chat (默认): DeepSeek 的旗舰对话模型，平衡性能和质量
- deepseek-coder: 专门针对代码生成和理解优化的模型
- deepseek-reasoner: 增强推理能力的模型，适合复杂问题解决

## 特性

- ✅ 完整兼容 CopilotKit Runtime API
- ✅ 支持流式响应和实时文本生成
- ✅ 支持并行和串行工具调用
- ✅ 自动温度范围限制（0.1-2.0）
- ✅ 角色转换（developer -> system）
- ✅ 完善的错误处理和日志记录
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from uuid import uuid4

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from .base import CopilotServiceAdapter
from ..types import (
    CopilotRuntimeChatCompletionRequest,
    CopilotRuntimeChatCompletionResponse,
)
from ..utils import (
    convert_action_to_openai_tool,
    convert_message_to_openai_message,
    limit_messages_to_token_count,
)
from ..events import EventSource

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekAdapter(CopilotServiceAdapter):
    """
    CopilotKit 运行时的 DeepSeek 适配器
    
    提供与 DeepSeek AI 模型的集成，包括 deepseek-chat、
    deepseek-coder 和 deepseek-reasoner 模型。
    
    此适配器负责：
    - 将 CopilotKit 请求转换为 DeepSeek API 调用
    - 处理流式响应和事件流
    - 管理工具调用和参数传递
    - 处理错误和异常情况
    - 提供完整的日志记录
    
    兼容性：
    - 与 TypeScript 版本的 DeepSeekAdapter 完全兼容
    - 支持所有 OpenAI 兼容的参数和配置
    - 自动处理 DeepSeek 特定的限制和要求
    """
    
    def __init__(
        self,
        openai: Optional[AsyncOpenAI] = None,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        disable_parallel_tool_calls: bool = False,
        base_url: str = DEEPSEEK_BASE_URL,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 DeepSeek 适配器
        
        参数:
            openai: 预配置的 AsyncOpenAI 实例，用于 DeepSeek API 调用
            api_key: DeepSeek API 密钥（如果未提供 openai 实例则必需）
            model: 要使用的 DeepSeek 模型
                   - deepseek-chat: 通用对话模型（默认）
                   - deepseek-coder: 代码专用模型
                   - deepseek-reasoner: 推理增强模型
            disable_parallel_tool_calls: 是否禁用并行工具调用
            base_url: 自定义 DeepSeek API 基础 URL
            headers: 发送请求时的额外头部信息
        
        异常:
            ValueError: 当未提供 openai 实例且缺少 api_key 时抛出
        
        使用示例:
            # 使用 API Key 初始化
            adapter = DeepSeekAdapter(api_key="sk-xxx", model="deepseek-chat")
            
            # 使用预配置客户端初始化
            client = AsyncOpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com/v1")
            adapter = DeepSeekAdapter(openai=client)
        """
        if openai:
            self._openai = openai
        else:
            if not api_key:
                raise ValueError("DeepSeek API key is required when openai instance is not provided")
            
            default_headers = {
                "User-Agent": "CopilotKit-DeepSeek-Adapter",
            }
            if headers:
                default_headers.update(headers)
                
            self._openai = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers,
            )
        
        self.model = model
        self.disable_parallel_tool_calls = disable_parallel_tool_calls
        
    @property
    def openai(self) -> AsyncOpenAI:
        """Get the OpenAI client instance."""
        return self._openai
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process chat completion request using DeepSeek."""
        thread_id = request.thread_id or str(uuid4())
        model = request.model or self.model
        messages = request.messages
        actions = request.actions
        event_source = request.event_source
        forwarded_parameters = request.forwarded_parameters or {}
        
        logger.info(
            "🔄 [DeepSeek] Processing request: thread_id=%s, model=%s, messages=%d, actions=%d",
            thread_id, model, len(messages), len(actions)
        )
        
        # Convert actions to OpenAI tools
        tools = [convert_action_to_openai_tool(action) for action in actions]
        
        # Filter messages using allowlist approach
        valid_tool_use_ids = set()
        
        # Extract valid tool_call IDs
        for message in messages:
            if message.is_action_execution_message():
                valid_tool_use_ids.add(message.id)
        
        # Filter messages, keeping only those with valid tool_call IDs
        filtered_messages = []
        for message in messages:
            if message.is_result_message():
                # Skip if there's no corresponding tool_call
                if message.action_execution_id not in valid_tool_use_ids:
                    continue
                # Remove this ID from valid IDs so we don't process duplicates
                valid_tool_use_ids.discard(message.action_execution_id)
            filtered_messages.append(message)
        
        # Convert to OpenAI messages
        openai_messages = [
            convert_message_to_openai_message(m, keep_system_role=True)
            for m in filtered_messages
        ]
        
        # DeepSeek compatibility fix: convert unsupported 'developer' role to 'system'
        for message in openai_messages:
            if isinstance(message, dict) and message.get("role") == "developer":
                logger.info("🔄 [DeepSeek] Converting developer role to system role")
                message["role"] = "system"
        
        # Limit messages to token count
        openai_messages = limit_messages_to_token_count(openai_messages, tools, model)
        
        # Prepare tool choice
        tool_choice = forwarded_parameters.get("tool_choice")
        if tool_choice == "function":
            tool_choice = {
                "type": "function",
                "function": {"name": forwarded_parameters.get("tool_choice_function_name")},
            }
        
        logger.info(
            "📤 [DeepSeek] Sending request to API: model=%s, messages=%d, tools=%d",
            model, len(openai_messages), len(tools)
        )
        
        try:
            # Prepare request payload
            request_payload = {
                "model": model,
                "stream": True,
                "messages": openai_messages,
            }
            
            if tools:
                request_payload["tools"] = tools
            
            if forwarded_parameters.get("max_tokens"):
                request_payload["max_tokens"] = forwarded_parameters["max_tokens"]
                
            if forwarded_parameters.get("stop"):
                request_payload["stop"] = forwarded_parameters["stop"]
                
            if tool_choice:
                request_payload["tool_choice"] = tool_choice
                
            if self.disable_parallel_tool_calls:
                request_payload["parallel_tool_calls"] = False
                
            if forwarded_parameters.get("temperature"):
                # DeepSeek temperature range: 0.1-2.0
                temperature = max(0.1, min(2.0, forwarded_parameters["temperature"]))
                request_payload["temperature"] = temperature
            
            logger.debug("📤 [DeepSeek] API Request payload: %s", json.dumps(request_payload, indent=2))
            
            # Create stream
            stream = await self._openai.chat.completions.create(**request_payload)
            
            logger.info("🔄 [DeepSeek] Stream created successfully, starting to process...")
            
            # Process stream
            await self._process_stream(stream, event_source, thread_id)
            
            return CopilotRuntimeChatCompletionResponse(thread_id=thread_id)
            
        except Exception as error:
            logger.error("❌ [DeepSeek] API error: %s", error)
            raise RuntimeError(f"DeepSeek API request failed: {error}")
    
    async def _process_stream(
        self,
        stream: AsyncGenerator[ChatCompletionChunk, None],
        event_source: EventSource,
        thread_id: str,
    ) -> None:
        """Process the streaming response from DeepSeek."""
        
        async def stream_handler(event_stream):
            mode = None  # "function" | "message" | None
            current_message_id = ""
            current_tool_call_id = ""
            current_action_name = ""
            
            try:
                logger.info("🔄 [DeepSeek] Starting stream iteration...")
                chunk_count = 0
                
                async for chunk in stream:
                    chunk_count += 1
                    
                    logger.debug(
                        "📦 [DeepSeek] Received chunk #%d: choices=%d, finish_reason=%s",
                        chunk_count,
                        len(chunk.choices),
                        chunk.choices[0].finish_reason if chunk.choices else None,
                    )
                    
                    if not chunk.choices:
                        continue
                    
                    choice = chunk.choices[0]
                    tool_call = choice.delta.tool_calls[0] if choice.delta.tool_calls else None
                    content = choice.delta.content
                    finish_reason = choice.finish_reason
                    
                    if finish_reason:
                        logger.info("🏁 [DeepSeek] Finish reason detected: %s", finish_reason)
                    
                    # Mode switching logic (from OpenAI adapter)
                    if mode == "message" and tool_call and tool_call.id:
                        logger.info("🔧 [DeepSeek] Switching from message to function mode")
                        mode = None
                        await event_stream.send_text_message_end(message_id=current_message_id)
                    elif mode == "function" and (not tool_call or tool_call.id):
                        logger.info("🔧 [DeepSeek] Switching from function to message mode")
                        mode = None
                        await event_stream.send_action_execution_end(
                            action_execution_id=current_tool_call_id
                        )
                    
                    # Start new mode if needed
                    if mode is None:
                        if tool_call and tool_call.id:
                            logger.info("🚀 [DeepSeek] Starting function mode")
                            mode = "function"
                            current_tool_call_id = tool_call.id
                            current_action_name = tool_call.function.name if tool_call.function else ""
                            await event_stream.send_action_execution_start(
                                action_execution_id=current_tool_call_id,
                                parent_message_id=chunk.id,
                                action_name=current_action_name,
                            )
                        elif content:
                            logger.info("💬 [DeepSeek] Starting message mode")
                            mode = "message"
                            current_message_id = chunk.id or str(uuid4())
                            await event_stream.send_text_message_start(message_id=current_message_id)
                    
                    # Send content events
                    if mode == "message" and content:
                        logger.debug("💬 [DeepSeek] Sending text content: %s", content)
                        await event_stream.send_text_message_content(
                            message_id=current_message_id,
                            content=content,
                        )
                    elif mode == "function" and tool_call and tool_call.function and tool_call.function.arguments:
                        logger.debug("📝 [DeepSeek] Sending function arguments: %s", tool_call.function.arguments)
                        await event_stream.send_action_execution_args(
                            action_execution_id=current_tool_call_id,
                            args=tool_call.function.arguments,
                        )
                    
                    # Break on finish reason
                    if finish_reason:
                        logger.info("🔚 [DeepSeek] Breaking loop due to finish reason: %s", finish_reason)
                        break
                
                # Send final end events
                logger.info("🏁 [DeepSeek] Stream loop ended after %d chunks, sending final events", chunk_count)
                
                if mode == "message":
                    logger.info("💬 [DeepSeek] Ending final text message")
                    await event_stream.send_text_message_end(message_id=current_message_id)
                elif mode == "function":
                    logger.info("🔧 [DeepSeek] Ending final function execution")
                    await event_stream.send_action_execution_end(
                        action_execution_id=current_tool_call_id
                    )
                    
            except Exception as error:
                logger.error("❌ [DeepSeek] streaming error: %s", error)
                
                # Error cleanup
                if mode == "message":
                    logger.info("💬 [DeepSeek] Error cleanup: ending text message")
                    await event_stream.send_text_message_end(message_id=current_message_id)
                elif mode == "function" and current_tool_call_id:
                    logger.info("🔧 [DeepSeek] Error cleanup: ending function execution")
                    await event_stream.send_action_execution_end(
                        action_execution_id=current_tool_call_id
                    )
                raise error
            
            # Complete event stream
            logger.info("🎉 [DeepSeek] Completing event stream")
            await event_stream.complete()
        
        await event_source.stream(stream_handler) 