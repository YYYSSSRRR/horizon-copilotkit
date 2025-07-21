"""Runtime-specific type definitions."""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Union, Awaitable, TYPE_CHECKING
from pydantic import BaseModel
from enum import Enum

from .messages import Message
from .actions import Action, Parameter

if TYPE_CHECKING:
    from .events import RuntimeEvent
    from ..events import RuntimeEventSource


class EndpointType(str, Enum):
    """Endpoint type enumeration."""
    COPILOTKIT = "copilotkit"
    LANGGRAPH_PLATFORM = "langgraph_platform"


class EndpointDefinition(BaseModel):
    """Base endpoint definition."""
    url: str
    type: Optional[EndpointType] = None
    
    class Config:
        arbitrary_types_allowed = True


class CopilotKitEndpoint(EndpointDefinition):
    """CopilotKit endpoint definition."""
    on_before_request: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True


class LangGraphPlatformEndpoint(EndpointDefinition):
    """LangGraph Platform endpoint definition."""
    deployment_url: str
    langsmith_api_key: str
    agents: Optional[List[str]] = None


class RemoteAgentAction(Action):
    """Remote agent action with handler."""
    remote_agent_handler: Callable[..., Awaitable[Any]]
    
    class Config:
        arbitrary_types_allowed = True


class Agent(BaseModel):
    """Agent definition."""
    name: str
    id: str
    description: str = ""


class CopilotRuntimeRequest(BaseModel):
    """Runtime request definition."""
    service_adapter: Any  # ServiceAdapter
    messages: List[Any]  # MessageInput
    actions: List[Any]  # ActionInput
    agent_session: Optional[Any] = None  # AgentSessionInput
    agent_states: Optional[List[Any]] = None  # AgentStateInput
    output_messages_promise: asyncio.Future
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    public_api_key: Optional[str] = None
    graphql_context: Dict[str, Any]
    forwarded_parameters: Optional[Any] = None  # ForwardedParametersInput
    url: Optional[str] = None
    extensions: Optional[Any] = None  # ExtensionsInput
    meta_events: Optional[List[Any]] = None  # MetaEventInput
    
    class Config:
        arbitrary_types_allowed = True


class CopilotRuntimeResponse(BaseModel):
    """Runtime response definition."""
    thread_id: str
    run_id: Optional[str] = None
    event_source: "RuntimeEventSource"
    server_side_actions: List[Action]
    action_inputs_without_agents: List[Any]  # ActionInput
    extensions: Optional[Any] = None  # ExtensionsResponse
    
    class Config:
        arbitrary_types_allowed = True


class LoadAgentStateResponse(BaseModel):
    """Load agent state response."""
    thread_id: str
    thread_exists: bool
    state: str  # JSON string
    messages: str  # JSON string


class ExtensionsResponse(BaseModel):
    """Extensions response model."""
    extensions: Optional[Dict[str, Any]] = None

