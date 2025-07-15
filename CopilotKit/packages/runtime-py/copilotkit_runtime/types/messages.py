"""
消息类型定义

对标TypeScript runtime中的所有消息相关类型
"""

import json
from typing import Any, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from .enums import MessageRole, MessageType


class BaseMessage(BaseModel):
    """基础消息类"""
    id: str = Field(..., description="消息ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")
    type: MessageType = Field(..., description="消息类型")

    def is_text_message(self) -> bool:
        """是否为文本消息"""
        return self.type == MessageType.TEXT_MESSAGE

    def is_action_execution_message(self) -> bool:
        """是否为动作执行消息"""
        return self.type == MessageType.ACTION_EXECUTION_MESSAGE

    def is_result_message(self) -> bool:
        """是否为结果消息"""
        return self.type == MessageType.RESULT_MESSAGE

    def is_agent_state_message(self) -> bool:
        """是否为代理状态消息"""
        return self.type == MessageType.AGENT_STATE_MESSAGE

    def is_image_message(self) -> bool:
        """是否为图片消息"""
        return self.type == MessageType.IMAGE_MESSAGE


class TextMessage(BaseMessage):
    """文本消息"""
    type: MessageType = Field(default=MessageType.TEXT_MESSAGE, description="消息类型")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class ActionExecutionMessage(BaseMessage):
    """动作执行消息"""
    type: MessageType = Field(default=MessageType.ACTION_EXECUTION_MESSAGE, description="消息类型")
    name: str = Field(..., description="动作名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="动作参数")


class ResultMessage(BaseMessage):
    """结果消息"""
    type: MessageType = Field(default=MessageType.RESULT_MESSAGE, description="消息类型")
    action_execution_id: str = Field(..., description="动作执行ID")
    action_name: str = Field(..., description="动作名称")
    result: str = Field(..., description="执行结果")

    @staticmethod
    def encode_result(
        result: Any,
        error: Optional[Union[str, Dict[str, str], Exception]] = None
    ) -> str:
        """编码结果"""
        error_obj = None
        if error:
            if isinstance(error, str):
                error_obj = {"code": "ERROR", "message": error}
            elif isinstance(error, Exception):
                error_obj = {"code": "ERROR", "message": str(error)}
            elif isinstance(error, dict):
                error_obj = error
        
        if error_obj:
            return json.dumps({
                "error": error_obj,
                "result": result or ""
            })
        
        if result is None:
            return ""
        
        return result if isinstance(result, str) else json.dumps(result)

    @staticmethod
    def decode_result(result: str) -> Dict[str, Any]:
        """解码结果"""
        if not result:
            return {"result": ""}
        
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "error" in parsed:
                return {
                    "error": parsed["error"],
                    "result": parsed.get("result", "")
                }
            return {"result": json.dumps(parsed) if not isinstance(parsed, str) else result}
        except json.JSONDecodeError:
            return {"result": result}

    def has_error(self) -> bool:
        """是否有错误"""
        try:
            decoded = self.decode_result(self.result)
            return "error" in decoded
        except:
            return False

    def get_error(self) -> Optional[Dict[str, str]]:
        """获取错误信息"""
        try:
            decoded = self.decode_result(self.result)
            return decoded.get("error")
        except:
            return None


class AgentStateMessage(BaseMessage):
    """代理状态消息"""
    type: MessageType = Field(default=MessageType.AGENT_STATE_MESSAGE, description="消息类型")
    thread_id: str = Field(..., description="线程ID")
    agent_name: str = Field(..., description="代理名称")
    node_name: str = Field(..., description="节点名称")
    run_id: str = Field(..., description="运行ID")
    active: bool = Field(..., description="是否活跃")
    role: MessageRole = Field(..., description="消息角色")
    state: Any = Field(..., description="状态数据")
    running: bool = Field(..., description="是否正在运行")


class ImageMessage(BaseMessage):
    """图片消息"""
    type: MessageType = Field(default=MessageType.IMAGE_MESSAGE, description="消息类型")
    role: MessageRole = Field(..., description="消息角色")
    bytes: str = Field(..., description="图片字节数据(Base64编码)")
    format: str = Field(..., description="图片格式")


# 消息联合类型
Message = Union[
    TextMessage,
    ActionExecutionMessage,
    ResultMessage,
    AgentStateMessage,
    ImageMessage
] 