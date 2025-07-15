"""
状态类型定义

对标TypeScript runtime中的状态相关类型
"""

from pydantic import BaseModel, Field
from .enums import MessageStatusCode


class BaseMessageStatus(BaseModel):
    """基础消息状态"""
    code: MessageStatusCode = Field(..., description="状态码")


class PendingMessageStatus(BaseMessageStatus):
    """待处理消息状态"""
    code: MessageStatusCode = Field(default=MessageStatusCode.PENDING, description="状态码")


class SuccessMessageStatus(BaseMessageStatus):
    """成功消息状态"""
    code: MessageStatusCode = Field(default=MessageStatusCode.SUCCESS, description="状态码")


class FailedMessageStatus(BaseMessageStatus):
    """失败消息状态"""
    code: MessageStatusCode = Field(default=MessageStatusCode.FAILED, description="状态码")
    reason: str = Field(..., description="失败原因") 