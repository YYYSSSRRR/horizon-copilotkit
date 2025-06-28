"""
Google adapter for CopilotKit Python Runtime

This module provides an adapter for Google's Gemini API.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
import google.generativeai as genai

from .base import (
    CopilotServiceAdapter,
    CopilotRuntimeChatCompletionRequest,
    CopilotRuntimeChatCompletionResponse,
)
from ..types import Message, MessageRole, ActionInput
from ..events import RuntimeEventSource, RuntimeEventTypes
from ..utils import random_id


class GoogleAdapter(CopilotServiceAdapter):
    """Google Gemini service adapter"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-pro",
        **kwargs: Any,
    ):
        if api_key:
            genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process Google Gemini chat completion request"""
        
        # Convert messages to Google format
        google_messages = self._convert_messages_to_google(request.messages)
        
        # Prepare Google request
        try:
            # Start generation
            response = await self.model.generate_content_async(
                google_messages,
                stream=True,
            )
            
            # Process stream in background
            asyncio.create_task(
                self._process_stream(response, request.event_source, request.thread_id)
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
        response: AsyncIterator[Any],
        event_source: RuntimeEventSource,
        thread_id: Optional[str],
    ) -> None:
        """Process Google stream and emit events"""
        
        try:
            message_id = random_id()
            content_buffer = ""
            
            async for chunk in response:
                if chunk.text:
                    content_buffer += chunk.text
                    event_source.emit(RuntimeEventTypes.MESSAGE_CHUNK, {
                        "id": message_id,
                        "content": chunk.text,
                        "thread_id": thread_id,
                    })
            
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
        
        except Exception as e:
            event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
    
    def _convert_messages_to_google(self, messages: List[Message]) -> List[str]:
        """Convert CopilotKit messages to Google format"""
        google_messages = []
        
        for message in messages:
            if message.text_message:
                google_messages.append(message.text_message.content)
        
        return google_messages 