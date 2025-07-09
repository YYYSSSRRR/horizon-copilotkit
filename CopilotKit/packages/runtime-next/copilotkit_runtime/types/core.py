"""
核心类型定义，对标 TypeScript 版本的基础类型。
"""

from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class BaseType(BaseModel):
    """
    基础类型
    
    所有自定义类型的基类，提供通用配置和方法。
    """
    model_config = ConfigDict(
        # 允许使用字段别名
        populate_by_name=True,
        # 验证赋值
        validate_assignment=True,
        # 严格模式
        strict=False,
        # 额外字段处理
        extra='forbid'
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(by_alias=True, exclude_none=True)
    
    def to_json_str(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class ParameterType(str, Enum):
    """参数类型枚举"""
    STRING = "string"
    NUMBER = "number" 
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class Parameter(BaseType):
    """动作参数定义"""
    name: str = Field(..., description="参数名称")
    type: ParameterType = Field(..., description="参数类型")
    description: Optional[str] = Field(None, description="参数描述")
    required: bool = Field(True, description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    enum: Optional[List[Any]] = Field(None, description="枚举值")
    properties: Optional[Dict[str, "Parameter"]] = Field(None, description="对象属性（当type为object时）")
    items: Optional["Parameter"] = Field(None, description="数组项类型（当type为array时）")
    
    class Config:
        json_encoders = {
            ParameterType: lambda v: v.value
        }


class RuntimeConfig(BaseType):
    """运行时配置"""
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: Optional[float] = Field(None, description="温度参数")
    top_p: Optional[float] = Field(None, description="Top-p参数")
    stop: Optional[List[str]] = Field(None, description="停止词")
    stream: bool = Field(False, description="是否启用流式响应")
    timeout: int = Field(30, description="请求超时时间（秒）")
    
    
class ForwardedParameters(BaseType):
    """转发给LLM的参数"""
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    tool_choice_function_name: Optional[str] = None


# 为了支持递归定义，需要更新模型
Parameter.model_rebuild() 