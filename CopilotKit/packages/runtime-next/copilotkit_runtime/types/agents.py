"""
代理相关类型定义。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """代理定义"""
    name: str = Field(..., description="代理名称")
    id: str = Field(..., description="代理ID")
    description: Optional[str] = Field(None, description="代理描述")


class AgentState(BaseModel):
    """代理状态"""
    agent_name: str = Field(..., description="代理名称")
    state: Dict[str, Any] = Field(default_factory=dict, description="状态数据")
    running: bool = Field(False, description="是否运行中")
    active: bool = Field(False, description="是否活跃")
    thread_id: str = Field(..., description="线程ID")
    node_name: Optional[str] = Field(None, description="节点名称")
    run_id: Optional[str] = Field(None, description="运行ID")


class AgentSession(BaseModel):
    """代理会话"""
    agent_name: str = Field(..., description="代理名称")
    thread_id: str = Field(..., description="线程ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="会话配置") 