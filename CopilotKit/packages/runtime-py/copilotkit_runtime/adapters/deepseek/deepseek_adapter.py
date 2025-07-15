"""
DeepSeek适配器

Copilot Runtime的DeepSeek适配器实现，对标TypeScript版本。

示例使用:
```python
from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter

# 创建DeepSeek适配器
deepseek_adapter = DeepSeekAdapter(
    api_key="your-deepseek-api-key",
    model="deepseek-chat"
)
```

支持的模型:
- deepseek-chat (默认): DeepSeek的旗舰聊天模型
- deepseek-coder: 专门用于代码生成和理解
- deepseek-reasoner: 增强推理能力
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator

import httpx
from pydantic import BaseModel, Field

from copilotkit_runtime.types import (
    CopilotServiceAdapter,
    AdapterRequest,
    AdapterResponse,
    Message,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage,
    MessageRole,
    MessageType,
    RuntimeEventTypes,
    ActionInput
)
from copilotkit_runtime.streaming import StreamingResponse, EventSource
from copilotkit_runtime.utils import random_id, convert_actions_to_tools, convert_messages_to_openai

# 常量定义
DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

logger = logging.getLogger(__name__)


class DeepSeekAdapterParams(BaseModel):
    """DeepSeek适配器参数"""
    api_key: Optional[str] = Field(None, description="DeepSeek API密钥")
    model: str = Field(default=DEFAULT_MODEL, description="使用的模型")
    disable_parallel_tool_calls: bool = Field(default=False, description="是否禁用并行工具调用")
    base_url: str = Field(default=DEEPSEEK_BASE_URL, description="API基础URL")
    headers: Optional[Dict[str, str]] = Field(None, description="额外的请求头")
    timeout: int = Field(default=60, description="请求超时时间(秒)")


class DeepSeekAdapter(CopilotServiceAdapter):
    """DeepSeek服务适配器"""
    
    def __init__(self, params: Optional[DeepSeekAdapterParams] = None, **kwargs):
        """
        初始化DeepSeek适配器
        
        Args:
            params: 适配器参数
            **kwargs: 其他参数，会覆盖params中的同名参数
        """
        if params is None:
            params = DeepSeekAdapterParams()
        
        # 处理kwargs参数
        for key, value in kwargs.items():
            if hasattr(params, key):
                setattr(params, key, value)
        
        self.params = params
        self.model = params.model
        self.disable_parallel_tool_calls = params.disable_parallel_tool_calls
        
        # 初始化HTTP客户端
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {params.api_key}",
        }
        
        if params.headers:
            headers.update(params.headers)
        
        self.client = httpx.AsyncClient(
            base_url=params.base_url,
            headers=headers,
            timeout=params.timeout
        )
        
        logger.info(f"🚀 [DeepSeek] 适配器初始化完成: {params.model}")
    
    def get_model(self) -> str:
        """获取默认模型名称"""
        return self.model
    
    def supports_streaming(self) -> bool:
        """是否支持流式响应"""
        return True
    
    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        return True
    
    async def process(self, request: AdapterRequest) -> AdapterResponse:
        """
        处理聊天完成请求
        
        Args:
            request: 适配器请求
            
        Returns:
            适配器响应
        """
        thread_id = request.thread_id or random_id()
        model = request.model or self.model
        
        logger.info(f"🔄 [DeepSeek] 处理请求: thread_id={thread_id}, model={model}, "
                   f"messages={len(request.messages)}, actions={len(request.actions)}")
        
        # 转换动作为工具
        tools = convert_actions_to_tools(request.actions)
        
        # 过滤和处理消息
        filtered_messages = self._filter_messages(request.messages)
        openai_messages = convert_messages_to_openai(filtered_messages, keep_system_role=True)
        
        # DeepSeek兼容性修复：将developer角色转换为system
        openai_messages = self._fix_deepseek_compatibility(openai_messages)
        
        # 准备API请求
        api_request = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
            "temperature": 0.7,
        }
        
        if tools:
            api_request["tools"] = tools
            if not self.disable_parallel_tool_calls:
                api_request["parallel_tool_calls"] = True
        
        # 处理转发参数
        if request.forwarded_parameters:
            tool_choice = request.forwarded_parameters.get("toolChoice")
            if tool_choice == "function":
                api_request["tool_choice"] = {
                    "type": "function",
                    "function": {"name": request.forwarded_parameters.get("toolChoiceFunctionName")}
                }
            elif tool_choice:
                api_request["tool_choice"] = tool_choice
        
        logger.debug(f"📤 [DeepSeek] 发送API请求: {model}, messages={len(openai_messages)}, tools={len(tools)}")
        
        # 发送流式请求
        try:
            response = await self._stream_completion(api_request)
            return AdapterResponse(
                messages=response,
                thread_id=thread_id,
                run_id=request.run_id
            )
        except Exception as e:
            logger.error(f"❌ [DeepSeek] API请求失败: {e}")
            # 返回错误消息
            error_message = TextMessage(
                id=random_id(),
                role=MessageRole.ASSISTANT,
                content=f"抱歉，请求处理失败: {str(e)}",
                type=MessageType.TEXT_MESSAGE
            )
            return AdapterResponse(
                messages=[error_message],
                thread_id=thread_id,
                run_id=request.run_id
            )
    
    def _filter_messages(self, messages: List[Message]) -> List[Message]:
        """
        过滤消息，只保留有效的工具调用和结果
        
        对标TypeScript版本的ALLOWLIST方法
        """
        # 第一步：提取有效的工具调用ID
        valid_tool_use_ids = set()
        
        for message in messages:
            if message.is_action_execution_message():
                valid_tool_use_ids.add(message.id)
        
        # 第二步：过滤消息，只保留有效的工具结果
        filtered_messages = []
        
        for message in messages:
            if message.is_result_message():
                # 跳过没有对应工具调用的结果
                if message.action_execution_id not in valid_tool_use_ids:
                    continue
                # 移除已处理的ID，避免重复处理
                valid_tool_use_ids.discard(message.action_execution_id)
                filtered_messages.append(message)
            else:
                # 保留所有非工具结果消息
                filtered_messages.append(message)
        
        return filtered_messages
    
    def _fix_deepseek_compatibility(self, openai_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        DeepSeek兼容性修复：将developer角色转换为system
        """
        fixed_messages = []
        
        for message in openai_messages:
            if message.get("role") == "developer":
                logger.debug("🔄 [DeepSeek] 转换developer角色为system角色")
                message = {**message, "role": "system"}
            fixed_messages.append(message)
        
        return fixed_messages
    
    async def _stream_completion(self, api_request: Dict[str, Any]) -> List[Message]:
        """
        处理流式完成请求
        """
        messages = []
        current_message = None
        current_content = ""
        current_tool_calls = {}
        
        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=api_request,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API请求失败: {response.status_code} - {error_text}")
                
                async for chunk in response.aiter_lines():
                    if not chunk or chunk == "data: [DONE]":
                        continue
                    
                    if chunk.startswith("data: "):
                        chunk_data = chunk[6:]  # 移除"data: "前缀
                        
                        try:
                            data = json.loads(chunk_data)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            
                            # 处理内容流
                            if "content" in delta and delta["content"]:
                                if current_message is None:
                                    current_message = TextMessage(
                                        id=random_id(),
                                        role=MessageRole.ASSISTANT,
                                        content="",
                                        type=MessageType.TEXT_MESSAGE
                                    )
                                
                                current_content += delta["content"]
                                current_message.content = current_content
                            
                            # 处理工具调用
                            if "tool_calls" in delta:
                                for tool_call in delta["tool_calls"]:
                                    tool_id = tool_call.get("id")
                                    if tool_id:
                                        if tool_id not in current_tool_calls:
                                            current_tool_calls[tool_id] = {
                                                "id": tool_id,
                                                "name": "",
                                                "arguments": ""
                                            }
                                        
                                        function = tool_call.get("function", {})
                                        if "name" in function:
                                            current_tool_calls[tool_id]["name"] = function["name"]
                                        if "arguments" in function:
                                            current_tool_calls[tool_id]["arguments"] += function["arguments"]
                            
                            # 检查是否是最后一个chunk
                            finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                            if finish_reason:
                                # 添加文本消息
                                if current_message and current_content:
                                    messages.append(current_message)
                                
                                # 添加工具调用消息
                                for tool_call in current_tool_calls.values():
                                    if tool_call["name"] and tool_call["arguments"]:
                                        try:
                                            args = json.loads(tool_call["arguments"])
                                        except json.JSONDecodeError:
                                            args = {"raw": tool_call["arguments"]}
                                        
                                        tool_message = ActionExecutionMessage(
                                            id=tool_call["id"],
                                            name=tool_call["name"],
                                            arguments=args,
                                            type=MessageType.ACTION_EXECUTION_MESSAGE
                                        )
                                        messages.append(tool_message)
                                
                                break
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ [DeepSeek] JSON解析失败: {e}, chunk: {chunk_data}")
                            continue
        
        except Exception as e:
            logger.error(f"❌ [DeepSeek] 流式请求处理失败: {e}")
            raise
        
        logger.info(f"✅ [DeepSeek] 流式响应处理完成，生成消息数: {len(messages)}")
        return messages
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
    
    def __del__(self):
        """析构函数"""
        try:
            asyncio.create_task(self.close())
        except:
            pass 