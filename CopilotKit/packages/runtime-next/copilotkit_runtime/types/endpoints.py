"""
端点相关类型定义。
"""

from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class EndpointType(str, Enum):
    """端点类型枚举"""
    COPILOTKIT = "copilotkit"
    LANGGRAPH_PLATFORM = "langgraph_platform"


class BaseEndpointDefinition(BaseModel):
    """基础端点定义"""
    url: str = Field(..., description="端点URL")
    type: EndpointType = Field(..., description="端点类型")


class CopilotKitEndpoint(BaseEndpointDefinition):
    """CopilotKit端点定义"""
    type: EndpointType = Field(default=EndpointType.COPILOTKIT, description="端点类型")
    headers: Optional[Dict[str, str]] = Field(None, description="请求头")


class LangGraphEndpoint(BaseEndpointDefinition):
    """LangGraph端点定义"""
    type: EndpointType = Field(default=EndpointType.LANGGRAPH_PLATFORM, description="端点类型")
    deployment_url: str = Field(..., description="部署URL")
    langsmith_api_key: Optional[str] = Field(None, description="LangSmith API密钥")


# 端点定义联合类型
EndpointDefinition = Union[CopilotKitEndpoint, LangGraphEndpoint] 