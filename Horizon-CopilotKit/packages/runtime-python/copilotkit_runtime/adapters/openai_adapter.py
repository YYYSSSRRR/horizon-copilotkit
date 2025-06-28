"""
OpenAI adapter for CopilotKit Python Runtime

This module provides an adapter for OpenAI's API, maintaining compatibility
with the TypeScript version.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from .base import (
    CopilotServiceAdapter,
    CopilotRuntimeChatCompletionRequest,
    CopilotRuntimeChatCompletionResponse,
)
from ..types import Message, MessageRole, ActionInput
from ..events import RuntimeEventSource, RuntimeEventTypes
from ..utils import random_id


class OpenAIAdapter(CopilotServiceAdapter):
    """OpenAI service adapter"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            base_url=base_url,
            **kwargs,
        )
        self.model = model
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process OpenAI chat completion request"""
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai(request.messages)
        
        # Convert actions to OpenAI tools
        tools = self._convert_actions_to_tools(request.actions)
        
        # Prepare OpenAI request parameters
        params: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": openai_messages,
            "stream": True,
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        # Add forwarded parameters
        if request.forwarded_parameters and request.forwarded_parameters.openai_api_key:
            # Create a new client with the forwarded API key
            client = AsyncOpenAI(api_key=request.forwarded_parameters.openai_api_key)
        else:
            client = self.client
        
        try:
            # Start streaming response
            stream = await client.chat.completions.create(**params)
            
            # Process stream in background
            asyncio.create_task(
                self._process_stream(stream, request.event_source, request.thread_id)
            )
            
            return CopilotRuntimeChatCompletionResponse(
                thread_id=request.thread_id or random_id(),
                run_id=request.run_id,
                extensions=request.extensions,
            )
            
        except Exception as e:
            # Emit error event
            request.event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
            raise
    
    async def _process_stream(
        self,
        stream: AsyncIterator[ChatCompletionChunk],
        event_source: RuntimeEventSource,
        thread_id: Optional[str],
    ) -> None:
        """Process OpenAI stream and emit events"""
        
        try:
            message_id = random_id()
            content_buffer = ""
            tool_calls = {}
            
            async for chunk in stream:
                if not chunk.choices:
                    continue
                
                choice = chunk.choices[0]
                delta = choice.delta
                
                # Handle content
                if delta.content:
                    content_buffer += delta.content
                    event_source.emit(RuntimeEventTypes.MESSAGE_CHUNK, {
                        "id": message_id,
                        "content": delta.content,
                        "thread_id": thread_id,
                    })
                
                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if tool_call.id not in tool_calls:
                            tool_calls[tool_call.id] = {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name or "",
                                    "arguments": "",
                                },
                            }
                        
                        if tool_call.function.arguments:
                            tool_calls[tool_call.id]["function"]["arguments"] += (
                                tool_call.function.arguments
                            )
                
                # Handle finish
                if choice.finish_reason:
                    # Emit final message
                    if content_buffer:
                        event_source.emit(RuntimeEventTypes.MESSAGE, {
                            "id": message_id,
                            "content": content_buffer,
                            "role": "assistant",
                            "thread_id": thread_id,
                        })
                    
                    # Emit tool calls
                    for tool_call in tool_calls.values():
                        event_source.emit(RuntimeEventTypes.TOOL_CALL, {
                            "id": tool_call["id"],
                            "name": tool_call["function"]["name"],
                            "arguments": tool_call["function"]["arguments"],
                            "thread_id": thread_id,
                        })
                    
                    # Emit completion
                    event_source.emit(RuntimeEventTypes.COMPLETION, {
                        "finish_reason": choice.finish_reason,
                        "thread_id": thread_id,
                    })
                    break
        
        except Exception as e:
            event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
    
    def _convert_messages_to_openai(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert CopilotKit messages to OpenAI format"""
        openai_messages = []
        
        for message in messages:
            if message.text_message:
                openai_messages.append({
                    "role": message.text_message.role.value,
                    "content": message.text_message.content,
                })
            elif message.action_execution_message:
                openai_messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": random_id(),
                        "type": "function",
                        "function": {
                            "name": message.action_execution_message.name,
                            "arguments": message.action_execution_message.arguments,
                        },
                    }],
                })
            elif message.result_message:
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": message.result_message.action_execution_id,
                    "content": message.result_message.result,
                })
            elif message.image_message:
                openai_messages.append({
                    "role": message.image_message.role.value,
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{message.image_message.format};base64,{message.image_message.bytes}"
                            },
                        }
                    ],
                })
        
        return openai_messages
    
    def _convert_actions_to_tools(self, actions: List[ActionInput]) -> List[Dict[str, Any]]:
        """Convert CopilotKit actions to OpenAI tools format"""
        tools = []
        
        for action in actions:
            if action.json_schema:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": action.name,
                        "description": action.description or "",
                        "parameters": action.json_schema,
                    },
                })
        
        return tools 