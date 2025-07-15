"""
事件类型定义

对标TypeScript runtime中的事件系统
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from .enums import RuntimeEventTypes, MetaEventName, MessageRole
from .messages import Message


class RuntimeEvent(BaseModel):
    """运行时事件基类"""
    type: RuntimeEventTypes = Field(..., description="事件类型")


class TextMessageStartEvent(RuntimeEvent):
    """文本消息开始事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.TEXT_MESSAGE_START)
    message_id: str = Field(..., description="消息ID")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")


class TextMessageContentEvent(RuntimeEvent):
    """文本消息内容事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.TEXT_MESSAGE_CONTENT)
    message_id: str = Field(..., description="消息ID")
    content: str = Field(..., description="消息内容")


class TextMessageEndEvent(RuntimeEvent):
    """文本消息结束事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.TEXT_MESSAGE_END)
    message_id: str = Field(..., description="消息ID")


class ActionExecutionStartEvent(RuntimeEvent):
    """动作执行开始事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.ACTION_EXECUTION_START)
    action_execution_id: str = Field(..., description="动作执行ID")
    action_name: str = Field(..., description="动作名称")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")


class ActionExecutionArgsEvent(RuntimeEvent):
    """动作执行参数事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.ACTION_EXECUTION_ARGS)
    action_execution_id: str = Field(..., description="动作执行ID")
    args: str = Field(..., description="动作参数")


class ActionExecutionEndEvent(RuntimeEvent):
    """动作执行结束事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.ACTION_EXECUTION_END)
    action_execution_id: str = Field(..., description="动作执行ID")


class ActionExecutionResultEvent(RuntimeEvent):
    """动作执行结果事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.ACTION_EXECUTION_RESULT)
    action_name: str = Field(..., description="动作名称")
    action_execution_id: str = Field(..., description="动作执行ID")
    result: str = Field(..., description="执行结果")


class AgentStateMessageEvent(RuntimeEvent):
    """代理状态消息事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.AGENT_STATE_MESSAGE)
    thread_id: str = Field(..., description="线程ID")
    agent_name: str = Field(..., description="代理名称")
    node_name: str = Field(..., description="节点名称")
    run_id: str = Field(..., description="运行ID")
    active: bool = Field(..., description="是否活跃")
    role: str = Field(..., description="角色")
    state: str = Field(..., description="状态")
    running: bool = Field(..., description="是否正在运行")


class MetaEvent(RuntimeEvent):
    """元事件"""
    type: RuntimeEventTypes = Field(default=RuntimeEventTypes.META_EVENT)
    name: MetaEventName = Field(..., description="元事件名称")
    

class LangGraphInterruptEvent(MetaEvent):
    """LangGraph中断事件"""
    name: MetaEventName = Field(default=MetaEventName.LANGGRAPH_INTERRUPT_EVENT)
    value: str = Field(..., description="中断值")


class CopilotKitLangGraphInterruptEvent(MetaEvent):
    """CopilotKit LangGraph中断事件"""
    name: MetaEventName = Field(default=MetaEventName.COPILOTKIT_LANGGRAPH_INTERRUPT_EVENT)
    data: Dict[str, Any] = Field(..., description="事件数据")


class LangGraphInterruptResumeEvent(MetaEvent):
    """LangGraph中断恢复事件"""
    name: MetaEventName = Field(default=MetaEventName.LANGGRAPH_INTERRUPT_RESUME_EVENT)
    data: str = Field(..., description="恢复数据")


# 事件联合类型
RuntimeEventUnion = Union[
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ActionExecutionStartEvent,
    ActionExecutionArgsEvent,
    ActionExecutionEndEvent,
    ActionExecutionResultEvent,
    AgentStateMessageEvent,
    LangGraphInterruptEvent,
    CopilotKitLangGraphInterruptEvent,
    LangGraphInterruptResumeEvent
]


class RuntimeEventSource:
    """运行时事件源（对标TypeScript的Subject）"""
    
    def __init__(self):
        self._observers = []
    
    def subscribe(self, observer):
        """订阅事件"""
        self._observers.append(observer)
    
    def unsubscribe(self, observer):
        """取消订阅"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def next(self, event: RuntimeEventUnion):
        """发送下一个事件"""
        for observer in self._observers:
            if hasattr(observer, 'on_next'):
                observer.on_next(event)
    
    def error(self, error: Exception):
        """发送错误"""
        for observer in self._observers:
            if hasattr(observer, 'on_error'):
                observer.on_error(error)
    
    def complete(self):
        """完成事件流"""
        for observer in self._observers:
            if hasattr(observer, 'on_completed'):
                observer.on_completed() 