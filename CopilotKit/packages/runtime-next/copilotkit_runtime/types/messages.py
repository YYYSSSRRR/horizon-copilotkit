"""
消息类型定义，对标 react-core-next 的消息类型系统。
"""

from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import json

from .core import BaseType
from ..utils.common import generate_id


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    DEVELOPER = "developer"


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    ACTION_EXECUTION = "action_execution"
    RESULT = "result"
    AGENT_STATE = "agent_state"
    IMAGE = "image"


class MessageStatus(BaseModel):
    """消息状态"""
    code: str = Field("success", description="状态码")
    reason: Optional[str] = Field(None, description="原因")


class Message(BaseType):
    """
    消息基类
    
    所有消息类型都继承自此类，提供通用属性和方法。
    """
    id: str = Field(default_factory=generate_id, description="消息ID")
    type: MessageType = Field(..., description="消息类型")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    status: MessageStatus = Field(default_factory=MessageStatus, description="消息状态")
    
    def is_text_message(self) -> bool:
        """是否为文本消息"""
        return self.type == MessageType.TEXT
    
    def is_action_execution_message(self) -> bool:
        """是否为动作执行消息"""
        return self.type == MessageType.ACTION_EXECUTION
    
    def is_result_message(self) -> bool:
        """是否为结果消息"""
        return self.type == MessageType.RESULT
    
    def is_agent_state_message(self) -> bool:
        """是否为代理状态消息"""
        return self.type == MessageType.AGENT_STATE
    
    def is_image_message(self) -> bool:
        """是否为图片消息"""
        return self.type == MessageType.IMAGE
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            "id": self.id,
            "type": self.type,
            "createdAt": self.created_at.isoformat(),
            "status": self.status.dict(),
        }


class TextMessage(Message):
    """
    文本消息
    
    包含角色和文本内容。
    """
    type: Literal[MessageType.TEXT] = Field(MessageType.TEXT, description="消息类型")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            **super().to_json(),
            "role": self.role,
            "content": self.content,
            "parentMessageId": self.parent_message_id,
        }


class ActionExecutionMessage(Message):
    """
    动作执行消息
    
    表示执行某个动作的请求。
    """
    type: Literal[MessageType.ACTION_EXECUTION] = Field(MessageType.ACTION_EXECUTION, description="消息类型")
    name: str = Field(..., description="动作名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="动作参数")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            **super().to_json(),
            "name": self.name,
            "arguments": self.arguments,
            "parentMessageId": self.parent_message_id,
        }


class ResultMessage(Message):
    """
    结果消息
    
    表示动作执行的结果。
    """
    type: Literal[MessageType.RESULT] = Field(MessageType.RESULT, description="消息类型")
    action_execution_id: str = Field(..., description="动作执行ID")
    action_name: str = Field(..., description="动作名称")
    result: Any = Field(..., description="执行结果")
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            **super().to_json(),
            "actionExecutionId": self.action_execution_id,
            "actionName": self.action_name,
            "result": self._encode_result(self.result),
        }
    
    @staticmethod
    def _encode_result(result: Any) -> str:
        """编码结果为字符串"""
        if result is None:
            return ""
        elif isinstance(result, str):
            return result
        else:
            return json.dumps(result)
    
    @staticmethod
    def _decode_result(result: str) -> Any:
        """解码结果字符串为对象"""
        try:
            return json.loads(result)
        except:
            return result


class AgentStateMessage(Message):
    """
    代理状态消息
    
    表示代理的当前状态。
    """
    type: Literal[MessageType.AGENT_STATE] = Field(MessageType.AGENT_STATE, description="消息类型")
    agent_name: str = Field(..., description="代理名称")
    state: Any = Field(..., description="代理状态")
    running: bool = Field(..., description="是否运行中")
    thread_id: str = Field(..., description="线程ID")
    node_name: Optional[str] = Field(None, description="节点名称")
    run_id: Optional[str] = Field(None, description="运行ID")
    active: bool = Field(..., description="是否活跃")
    role: MessageRole = Field(MessageRole.ASSISTANT, description="消息角色")
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            **super().to_json(),
            "agentName": self.agent_name,
            "state": self.state,
            "running": self.running,
            "threadId": self.thread_id,
            "nodeName": self.node_name,
            "runId": self.run_id,
            "active": self.active,
            "role": self.role,
        }


class ImageMessage(Message):
    """
    图片消息
    
    包含图片数据。
    """
    type: Literal[MessageType.IMAGE] = Field(MessageType.IMAGE, description="消息类型")
    format: str = Field(..., description="图片格式")
    bytes: str = Field(..., description="图片数据（Base64编码）")
    role: MessageRole = Field(..., description="消息角色")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")
    
    def to_json(self) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            **super().to_json(),
            "format": self.format,
            "bytes": self.bytes,
            "role": self.role,
            "parentMessageId": self.parent_message_id,
        }


# 消息类型联合
MessageUnion = Union[TextMessage, ActionExecutionMessage, ResultMessage, AgentStateMessage, ImageMessage]


def create_message_from_json(data: Dict[str, Any]) -> Message:
    """
    从JSON数据创建消息对象
    
    Args:
        data: JSON数据
        
    Returns:
        消息对象
    """
    message_type = data.get("type")
    created_at = datetime.fromisoformat(data.get("createdAt", datetime.now().isoformat()))
    status = MessageStatus(**data.get("status", {"code": "success"}))
    
    if message_type == "text":
        return TextMessage(
            id=data.get("id"),
            created_at=created_at,
            status=status,
            role=data.get("role"),
            content=data.get("content"),
            parent_message_id=data.get("parentMessageId"),
        )
    elif message_type == "action_execution":
        return ActionExecutionMessage(
            id=data.get("id"),
            created_at=created_at,
            status=status,
            name=data.get("name"),
            arguments=data.get("arguments", {}),
            parent_message_id=data.get("parentMessageId"),
        )
    elif message_type == "result":
        return ResultMessage(
            id=data.get("id"),
            created_at=created_at,
            status=status,
            action_execution_id=data.get("actionExecutionId"),
            action_name=data.get("actionName", ""),
            result=ResultMessage._decode_result(data.get("result", "")),
        )
    elif message_type == "agent_state":
        return AgentStateMessage(
            id=data.get("id"),
            created_at=created_at,
            status=status,
            agent_name=data.get("agentName"),
            state=data.get("state"),
            running=data.get("running"),
            thread_id=data.get("threadId"),
            node_name=data.get("nodeName"),
            run_id=data.get("runId"),
            active=data.get("active", False),
            role=data.get("role", MessageRole.ASSISTANT),
        )
    elif message_type == "image":
        return ImageMessage(
            id=data.get("id"),
            created_at=created_at,
            status=status,
            format=data.get("format"),
            bytes=data.get("bytes"),
            role=data.get("role"),
            parent_message_id=data.get("parentMessageId"),
        )
    else:
        raise ValueError(f"Unknown message type: {message_type}")


def convert_json_to_messages(data: List[Dict[str, Any]]) -> List[Message]:
    """
    将JSON数据列表转换为消息对象列表
    
    Args:
        data: JSON数据列表
        
    Returns:
        消息对象列表
    """
    return [create_message_from_json(item) for item in data]


def convert_messages_to_json(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    将消息对象列表转换为JSON数据列表
    
    Args:
        messages: 消息对象列表
        
    Returns:
        JSON数据列表
    """
    return [message.to_json() for message in messages] 