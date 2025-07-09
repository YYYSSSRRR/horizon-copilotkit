"""
运行时事件系统实现。
"""

from typing import Any, Dict, Optional, AsyncIterator, Callable, Awaitable, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import asyncio
import json
from datetime import datetime


class RuntimeEvent(BaseModel):
    """运行时事件基类"""
    type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        })


class TextDeltaEvent(RuntimeEvent):
    """文本增量事件"""
    type: str = "text_delta"
    delta: str = Field(..., description="文本增量")
    
    def __init__(self, delta: str, **kwargs):
        super().__init__(data={"delta": delta}, **kwargs)
        self.delta = delta


class ActionExecutionEvent(RuntimeEvent):
    """动作执行事件"""
    type: str = "action_execution"
    action_name: str = Field(..., description="动作名称")
    action_id: str = Field(..., description="动作ID")
    arguments: Dict[str, Any] = Field(..., description="动作参数")
    
    def __init__(self, action_name: str, action_id: str, arguments: Dict[str, Any], **kwargs):
        super().__init__(data={
            "action_name": action_name,
            "action_id": action_id, 
            "arguments": arguments
        }, **kwargs)
        self.action_name = action_name
        self.action_id = action_id
        self.arguments = arguments


class ActionResultEvent(RuntimeEvent):
    """动作结果事件"""
    type: str = "action_result"
    action_id: str = Field(..., description="动作ID")
    result: Any = Field(..., description="执行结果")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    
    def __init__(self, action_id: str, result: Any, success: bool = True, error: Optional[str] = None, **kwargs):
        super().__init__(data={
            "action_id": action_id,
            "result": result,
            "success": success,
            "error": error
        }, **kwargs)
        self.action_id = action_id
        self.result = result
        self.success = success
        self.error = error


class RuntimeEventSource:
    """运行时事件源"""
    
    def __init__(self):
        self._callbacks: list[Callable[[AsyncIterator[RuntimeEvent]], Awaitable[None]]] = []
        self._events: list[RuntimeEvent] = []
        self._streaming = False
    
    def stream(self, callback: Callable[[AsyncIterator[RuntimeEvent]], Awaitable[None]]) -> None:
        """注册流式回调"""
        self._callbacks.append(callback)
    
    async def emit(self, event: RuntimeEvent) -> None:
        """发射事件"""
        self._events.append(event)
        
        if self._streaming:
            # 如果正在流式传输，立即发送事件
            for callback in self._callbacks:
                try:
                    await callback(self._create_single_event_iterator(event))
                except Exception as e:
                    print(f"Error in event callback: {e}")
    
    async def emit_text_delta(self, delta: str) -> None:
        """发射文本增量事件"""
        await self.emit(TextDeltaEvent(delta=delta))
    
    async def emit_action_execution(self, action_name: str, action_id: str, arguments: Dict[str, Any]) -> None:
        """发射动作执行事件"""
        await self.emit(ActionExecutionEvent(
            action_name=action_name,
            action_id=action_id,
            arguments=arguments
        ))
    
    async def emit_action_result(self, action_id: str, result: Any, success: bool = True, error: Optional[str] = None) -> None:
        """发射动作结果事件"""
        await self.emit(ActionResultEvent(
            action_id=action_id,
            result=result,
            success=success,
            error=error
        ))
    
    async def start_streaming(self) -> None:
        """开始流式传输"""
        self._streaming = True
        
        # 为每个回调创建事件迭代器
        for callback in self._callbacks:
            try:
                await callback(self._create_event_iterator())
            except Exception as e:
                print(f"Error in streaming callback: {e}")
    
    async def stop_streaming(self) -> None:
        """停止流式传输"""
        self._streaming = False
    
    async def _create_event_iterator(self) -> AsyncIterator[RuntimeEvent]:
        """创建事件迭代器"""
        # 首先发送已有的事件
        for event in self._events:
            yield event
        
        # 然后等待新事件
        while self._streaming:
            # 这里可以实现更复杂的事件队列逻辑
            await asyncio.sleep(0.01)  # 避免CPU占用过高
    
    async def _create_single_event_iterator(self, event: RuntimeEvent) -> AsyncIterator[RuntimeEvent]:
        """创建单个事件的迭代器"""
        yield event
    
    def get_events(self) -> list[RuntimeEvent]:
        """获取所有事件"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """清空事件"""
        self._events.clear() 