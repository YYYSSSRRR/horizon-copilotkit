"""
Endpoint definitions for CopilotKit Python Runtime

This module defines remote endpoint types and configurations.
"""

from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pydantic import BaseModel


class EndpointType(Enum):
    """Endpoint type enumeration"""
    COPILOT_KIT = "copilot_kit"
    LANGGRAPH_PLATFORM = "langgraph_platform"


class AgentConfig(BaseModel):
    """Agent configuration"""
    name: str
    description: str


class CopilotKitEndpoint(BaseModel):
    """CopilotKit endpoint configuration"""
    type: EndpointType = EndpointType.COPILOT_KIT
    url: str
    headers: Optional[Dict[str, str]] = None


class LangGraphPlatformEndpoint(BaseModel):
    """LangGraph Platform endpoint configuration"""
    type: EndpointType = EndpointType.LANGGRAPH_PLATFORM
    deployment_url: str
    langsmith_api_key: Optional[str] = None
    agents: List[AgentConfig]


EndpointDefinition = Union[CopilotKitEndpoint, LangGraphPlatformEndpoint]


def copilot_kit_endpoint(
    url: str,
    headers: Optional[Dict[str, str]] = None,
) -> CopilotKitEndpoint:
    """Create a CopilotKit endpoint configuration"""
    return CopilotKitEndpoint(
        type=EndpointType.COPILOT_KIT,
        url=url,
        headers=headers,
    )


def langgraph_platform_endpoint(
    deployment_url: str,
    langsmith_api_key: Optional[str] = None,
    agents: Optional[List[Dict[str, str]]] = None,
) -> LangGraphPlatformEndpoint:
    """Create a LangGraph Platform endpoint configuration"""
    agent_configs = []
    if agents:
        for agent in agents:
            agent_configs.append(AgentConfig(
                name=agent.get("name", ""),
                description=agent.get("description", "")
            ))
    
    return LangGraphPlatformEndpoint(
        type=EndpointType.LANGGRAPH_PLATFORM,
        deployment_url=deployment_url,
        langsmith_api_key=langsmith_api_key,
        agents=agent_configs,
    )


def resolve_endpoint_type(endpoint: EndpointDefinition) -> EndpointType:
    """Resolve endpoint type from endpoint definition"""
    return endpoint.type 