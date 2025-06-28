"""
LangChain adapter for CopilotKit Python Runtime

This module provides an adapter for LangChain models.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, Union, AsyncIterator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from .base import (
    CopilotServiceAdapter,
    CopilotRuntimeChatCompletionRequest,
    CopilotRuntimeChatCompletionResponse,
)
from ..types import Message, MessageRole, ActionInput
from ..events import RuntimeEventSource, RuntimeEventTypes
from ..utils import random_id


class LangChainAdapter(CopilotServiceAdapter):
    """LangChain service adapter"""
    
    def __init__(
        self,
        chain_fn: Callable[[List[BaseMessage], List[BaseTool]], Any],
        model: Optional[str] = None,
    ):
        self.chain_fn = chain_fn
        self.model = model
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process LangChain chat completion request"""
        
        # Convert messages to LangChain format
        langchain_messages = self._convert_messages_to_langchain(request.messages)
        
        # Convert actions to LangChain tools
        tools = self._convert_actions_to_tools(request.actions)
        
        try:
            # Execute chain function
            response = self.chain_fn(langchain_messages, tools)
            
            # Process response in background
            asyncio.create_task(
                self._process_response(response, request.event_source, request.thread_id)
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
    
    async def _process_response(
        self,
        response: Any,
        event_source: RuntimeEventSource,
        thread_id: Optional[str],
    ) -> None:
        """Process LangChain response and emit events"""
        
        try:
            message_id = random_id()
            content_buffer = ""
            
            # Handle different response types
            if hasattr(response, '__aiter__'):
                # Streaming response
                async for chunk in response:
                    if hasattr(chunk, 'content') and chunk.content:
                        content_buffer += chunk.content
                        event_source.emit(RuntimeEventTypes.MESSAGE_CHUNK, {
                            "id": message_id,
                            "content": chunk.content,
                            "thread_id": thread_id,
                        })
            else:
                # Non-streaming response
                if hasattr(response, 'content'):
                    content_buffer = response.content
                elif isinstance(response, str):
                    content_buffer = response
            
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
    
    def _convert_messages_to_langchain(self, messages: List[Message]) -> List[BaseMessage]:
        """Convert CopilotKit messages to LangChain format"""
        langchain_messages = []
        
        for message in messages:
            if message.text_message:
                if message.text_message.role == MessageRole.USER:
                    langchain_messages.append(HumanMessage(content=message.text_message.content))
                elif message.text_message.role == MessageRole.ASSISTANT:
                    langchain_messages.append(AIMessage(content=message.text_message.content))
                elif message.text_message.role == MessageRole.SYSTEM:
                    langchain_messages.append(SystemMessage(content=message.text_message.content))
        
        return langchain_messages
    
    def _convert_actions_to_tools(self, actions: List[ActionInput]) -> List[BaseTool]:
        """Convert CopilotKit actions to LangChain tools format"""
        # This is a simplified implementation
        # In practice, you'd need to create proper LangChain tools
        tools = []
        # TODO: Implement proper tool conversion
        return tools 