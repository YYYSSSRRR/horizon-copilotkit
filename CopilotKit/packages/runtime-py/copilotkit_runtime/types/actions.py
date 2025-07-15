"""
动作类型定义

对标TypeScript runtime中的动作系统
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from pydantic import BaseModel, Field
from .enums import ActionInputAvailability


class Parameter(BaseModel):
    """参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    description: Optional[str] = Field(None, description="参数描述")
    required: bool = Field(default=True, description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    enum: Optional[List[str]] = Field(None, description="枚举值")


class ActionInput(BaseModel):
    """动作输入定义"""
    name: str = Field(..., description="动作名称")
    description: str = Field(..., description="动作描述")
    parameters: List[Parameter] = Field(default_factory=list, description="参数列表")
    availability: ActionInputAvailability = Field(
        default=ActionInputAvailability.ENABLED,
        description="可用性状态"
    )
    handler: Optional[Callable] = Field(None, description="处理函数", exclude=True)


class Action(BaseModel):
    """动作定义"""
    name: str = Field(..., description="动作名称")
    description: str = Field(..., description="动作描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数schema")
    handler: Optional[Callable[..., Awaitable[Any]]] = Field(None, exclude=True)

    class Config:
        arbitrary_types_allowed = True


class ActionResult(BaseModel):
    """动作执行结果"""
    action_name: str = Field(..., description="动作名称")
    action_execution_id: str = Field(..., description="执行ID")
    result: Any = Field(..., description="执行结果")
    error: Optional[Dict[str, str]] = Field(None, description="错误信息") 