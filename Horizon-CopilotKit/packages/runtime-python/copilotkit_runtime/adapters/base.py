"""
Base adapter interface for CopilotKit Python Runtime

This module defines the base interface that all service adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, AsyncIterator
from ..types import (
    Message,
    ActionInput,
    ForwardedParametersInput,
    ExtensionsInput,
    ExtensionsResponse,
    AgentSessionInput,
    AgentStateInput,
)
from ..events import RuntimeEventSource


class CopilotKitResponse:
    """Response from CopilotKit processing"""
    
    def __init__(self, stream: AsyncIterator[bytes], headers: Optional[Dict[str, str]] = None):
        self.stream = stream
        self.headers = headers or {}


class CopilotRuntimeChatCompletionRequest:
    """Chat completion request type"""
    
    def __init__(
        self,
        event_source: RuntimeEventSource,
        messages: list[Message],
        actions: list[ActionInput],
        model: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        forwarded_parameters: Optional[ForwardedParametersInput] = None,
        extensions: Optional[ExtensionsInput] = None,
        agent_session: Optional[AgentSessionInput] = None,
        agent_states: Optional[list[AgentStateInput]] = None,
    ):
        self.event_source = event_source
        self.messages = messages
        self.actions = actions
        self.model = model
        self.thread_id = thread_id
        self.run_id = run_id
        self.forwarded_parameters = forwarded_parameters
        self.extensions = extensions
        self.agent_session = agent_session
        self.agent_states = agent_states


class CopilotRuntimeChatCompletionResponse:
    """Chat completion response type"""
    
    def __init__(
        self,
        thread_id: str,
        run_id: Optional[str] = None,
        extensions: Optional[ExtensionsResponse] = None,
    ):
        self.thread_id = thread_id
        self.run_id = run_id
        self.extensions = extensions


class CopilotServiceAdapter(ABC):
    """Abstract base class for all service adapters"""
    
    @abstractmethod
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process a chat completion request"""
        pass


class EmptyAdapter(CopilotServiceAdapter):
    """Empty adapter for agent-only mode"""
    
    async def process(
        self, request: CopilotRuntimeChatCompletionRequest
    ) -> CopilotRuntimeChatCompletionResponse:
        """Process request - should not be called for EmptyAdapter"""
        raise RuntimeError("EmptyAdapter should not process requests directly") 