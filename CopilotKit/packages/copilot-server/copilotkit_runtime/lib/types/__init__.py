"""Type definitions and data models."""

from .messages import Message, Role
from .actions import ActionInput, ActionResult, Action, Parameter
from .agents import AgentState
from .streaming import StreamingResponse
# Delayed import to avoid circular dependencies
# from .events import RuntimeEvent, RuntimeEventTypes
from .runtime import (
    EndpointType,
    EndpointDefinition,
    CopilotKitEndpoint,
    LangGraphPlatformEndpoint,
    RemoteAgentAction,
    Agent,
    CopilotRuntimeRequest,
    CopilotRuntimeResponse,
    LoadAgentStateResponse,
    ExtensionsResponse
)
from ..events import RuntimeEventSource

# Rebuild models after all imports are complete
def _rebuild_models():
    """Rebuild models to resolve forward references."""
    from .runtime import CopilotRuntimeResponse
    from ..events import RuntimeEventSource
    # Update the annotation to use the actual class
    CopilotRuntimeResponse.model_fields['event_source'].annotation = RuntimeEventSource
    CopilotRuntimeResponse.model_rebuild()

_rebuild_models()

__all__ = [
    "Message",
    "Role",
    "ActionInput",
    "ActionResult",
    "Action",
    "Parameter", 
    "AgentState",
    "StreamingResponse",
    # "RuntimeEvent",
    # "RuntimeEventTypes",
    "EndpointType",
    "EndpointDefinition",
    "CopilotKitEndpoint",
    "LangGraphPlatformEndpoint",
    "RemoteAgentAction",
    "RuntimeEventSource",
    "Agent",
    "CopilotRuntimeRequest",
    "CopilotRuntimeResponse",
    "LoadAgentStateResponse",
    "ExtensionsResponse"
]