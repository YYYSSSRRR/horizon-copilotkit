"""
Anthropic adapter for CopilotKit Python Runtime

This module provides an adapter for Anthropic's Claude API.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from anthropic import AsyncAnthropic

from .base import (
    CopilotServiceAdapter,
    CopilotRuntimeChatCompletionRequest,
    CopilotRuntimeChatCompletionResponse,
)
from ..types import Message, MessageRole, ActionInput
from ..events import RuntimeEventSource, RuntimeEventTypes
from ..utils import random_id


class AnthropicAdapter(CopilotServiceAdapter):
    """Anthropic Claude service adapter"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs: Any,
    ):
        self.client = AsyncAnthropic(api_key=api_key, **kwargs)
        self.model = model
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process Anthropic chat completion request"""
        
        # Convert messages to Anthropic format
        anthropic_messages = self._convert_messages_to_anthropic(request.messages)
        
        # Convert actions to Anthropic tools
        tools = self._convert_actions_to_tools(request.actions)
        
        # Prepare Anthropic request parameters
        params: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "stream": True,
        }
        
        if tools:
            params["tools"] = tools
        
        # Add forwarded parameters
        if request.forwarded_parameters and request.forwarded_parameters.anthropic_api_key:
            client = AsyncAnthropic(api_key=request.forwarded_parameters.anthropic_api_key)
        else:
            client = self.client
        
        try:
            # Start streaming response
            stream = await client.messages.create(**params)
            
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
            request.event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
            raise
    
    async def _process_stream(
        self,
        stream: AsyncIterator[Any],
        event_source: RuntimeEventSource,
        thread_id: Optional[str],
    ) -> None:
        """Process Anthropic stream and emit events"""
        
        try:
            message_id = random_id()
            content_buffer = ""
            
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        content_buffer += event.delta.text
                        event_source.emit(RuntimeEventTypes.MESSAGE_CHUNK, {
                            "id": message_id,
                            "content": event.delta.text,
                            "thread_id": thread_id,
                        })
                elif event.type == "message_stop":
                    # Emit final message
                    if content_buffer:
                        event_source.emit(RuntimeEventTypes.MESSAGE, {
                            "id": message_id,
                            "content": content_buffer,
                            "role": "assistant",
                            "thread_id": thread_id,
                        })
                    
                    # Emit completion
                    event_source.emit(RuntimeEventTypes.COMPLETION, {
                        "finish_reason": "stop",
                        "thread_id": thread_id,
                    })
                    break
        
        except Exception as e:
            event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
    
    def _convert_messages_to_anthropic(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert CopilotKit messages to Anthropic format"""
        anthropic_messages = []
        
        for message in messages:
            if message.text_message:
                # Skip system messages - they need special handling
                if message.text_message.role != MessageRole.SYSTEM:
                    anthropic_messages.append({
                        "role": "user" if message.text_message.role == MessageRole.USER else "assistant",
                        "content": message.text_message.content,
                    })
        
        return anthropic_messages
    
    def _convert_actions_to_tools(self, actions: List[ActionInput]) -> List[Dict[str, Any]]:
        """Convert CopilotKit actions to Anthropic tools format"""
        tools = []
        
        for action in actions:
            if action.json_schema:
                tools.append({
                    "name": action.name,
                    "description": action.description or "",
                    "input_schema": action.json_schema,
                })
        
        return tools 