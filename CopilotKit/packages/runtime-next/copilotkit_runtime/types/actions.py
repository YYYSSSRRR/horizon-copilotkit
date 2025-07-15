"""
动作相关类型定义。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from pydantic import BaseModel, Field
from .core import Parameter, BaseType


class ActionAvailability(str, Enum):
    """动作可用性枚举"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    REMOTE = "remote"


class ActionInput(BaseType):
    """动作输入定义"""
    name: str = Field(..., description="动作名称")
    description: Optional[str] = Field(None, description="动作描述")
    parameters: List[Parameter] = Field(default_factory=list, description="参数列表")
    
    def to_json_schema(self) -> Dict[str, Any]:
        """转换为JSON Schema格式"""
        required_params = [p.name for p in self.parameters if p.required]
        properties = {p.name: self._parameter_to_schema(p) for p in self.parameters}
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                }
            }
        }
    
    def _parameter_to_schema(self, param: Parameter) -> Dict[str, Any]:
        """将参数转换为JSON Schema"""
        schema = {"type": param.type.value}
        
        if param.description:
            schema["description"] = param.description
        
        if param.enum:
            schema["enum"] = param.enum
        
        if param.default is not None:
            schema["default"] = param.default
        
        if param.type.value == "array" and param.items:
            schema["items"] = self._parameter_to_schema(param.items)
        
        if param.type.value == "object" and param.properties:
            schema["properties"] = {
                k: self._parameter_to_schema(v) for k, v in param.properties.items()
            }
            required_props = [k for k, v in param.properties.items() if v.required]
            if required_props:
                schema["required"] = required_props
        
        return schema


# 动作处理函数类型
ActionHandler = Callable[[Dict[str, Any]], Union[Any, Awaitable[Any]]]


class Action(BaseType):
    """动作定义"""
    name: str = Field(..., description="动作名称")
    description: Optional[str] = Field(None, description="动作描述")
    parameters: List[Parameter] = Field(default_factory=list, description="参数列表")
    handler: Optional[ActionHandler] = Field(None, description="处理函数", exclude=True)
    
    model_config = BaseType.model_config.copy()
    model_config.update({"arbitrary_types_allowed": True})
    
    def to_action_input(self) -> ActionInput:
        """转换为ActionInput"""
        return ActionInput(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行动作"""
        if not self.handler:
            raise ValueError(f"Action {self.name} has no handler")
        
        # 如果handler是async函数，await它
        import asyncio
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(arguments)
        else:
            return self.handler(arguments)


class ActionResult(BaseType):
    """动作执行结果"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    
    @classmethod
    def success_result(cls, result: Any, execution_time: Optional[float] = None) -> "ActionResult":
        """创建成功结果"""
        return cls(success=True, result=result, execution_time=execution_time)
    
    @classmethod
    def error_result(cls, error: str, execution_time: Optional[float] = None) -> "ActionResult":
        """创建错误结果"""
        return cls(success=False, error=error, execution_time=execution_time) 