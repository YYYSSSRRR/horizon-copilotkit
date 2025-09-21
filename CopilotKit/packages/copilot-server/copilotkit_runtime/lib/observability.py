"""Observability and logging configuration."""

from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from typing import Protocol


class LLMRequestData(BaseModel):
    """LLM request data for logging."""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    model: Optional[str] = None
    messages: List[Any] = []
    actions: List[Any] = []
    forwarded_parameters: Optional[Any] = None
    timestamp: int
    provider: Optional[str] = None
    agent_name: Optional[str] = None
    node_name: Optional[str] = None


class LLMResponseData(BaseModel):
    """LLM response data for logging."""
    thread_id: str
    run_id: Optional[str] = None
    model: Optional[str] = None
    output: Any
    latency: int
    timestamp: int
    provider: Optional[str] = None
    is_final_response: Optional[bool] = None
    is_progressive_chunk: Optional[bool] = None
    agent_name: Optional[str] = None
    node_name: Optional[str] = None


class LLMErrorData(BaseModel):
    """LLM error data for logging."""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    model: Optional[str] = None
    error: Exception
    timestamp: int
    latency: int
    provider: Optional[str] = None
    agent_name: Optional[str] = None
    node_name: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class ObservabilityHooks(Protocol):
    """Protocol for observability hooks."""
    
    async def handle_request(self, data: LLMRequestData) -> None:
        """Handle LLM request logging."""
        ...
    
    async def handle_response(self, data: LLMResponseData) -> None:
        """Handle LLM response logging."""
        ...
    
    async def handle_error(self, data: LLMErrorData) -> None:
        """Handle LLM error logging."""
        ...


class CopilotObservabilityConfig(BaseModel):
    """Configuration for observability."""
    enabled: bool = False
    progressive: bool = True
    hooks: Optional[Any] = None  # ObservabilityHooks protocol
    
    class Config:
        arbitrary_types_allowed = True