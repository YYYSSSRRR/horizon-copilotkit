"""
事件源处理

对标TypeScript的agents/langgraph/event-source.ts实现
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Callable
from datetime import datetime

import reactivex as rx
from reactivex import operators as ops

from ..types.events import RuntimeEvent
from ..types.enums import (
    RuntimeEventTypes,
    LangGraphEventTypes,
    MessageRole,
    MessageType
)
from ..types.messages import (
    Message,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage
)
from ..utils import random_id

logger = logging.getLogger(__name__)


class LangGraphEvent:
    """LangGraph事件"""
    
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.utcnow()


class EventSource:
    """
    事件源处理器
    
    对标TypeScript的agents/langgraph/event-source.ts
    处理LangGraph和其他外部系统的事件流
    """
    
    def __init__(self):
        self._subject = rx.subject.Subject()
        self._observers = []
        self._running = False
        self._message_buffer = []
        self._current_message = None
        self._current_tool_calls = {}
    
    def subscribe(self, observer: Callable[[RuntimeEvent], None]):
        """订阅事件"""
        self._observers.append(observer)
        return self._subject.subscribe(observer)
    
    def emit(self, event: RuntimeEvent):
        """发出事件"""
        if not self._running:
            return
        
        logger.debug(f"📡 发出事件: {event.type if hasattr(event, 'type') else type(event)}")
        
        # 通知所有观察者
        for observer in self._observers:
            try:
                observer(event)
            except Exception as e:
                logger.error(f"观察者处理事件时出错: {e}")
        
        # 推送到RxPY主题
        self._subject.on_next(event)
    
    def start(self):
        """启动事件源"""
        self._running = True
        logger.info("🚀 事件源已启动")
    
    def stop(self):
        """停止事件源"""
        self._running = False
        self._subject.on_completed()
        logger.info("⏹️ 事件源已停止")
    
    def error(self, error: Exception):
        """发出错误"""
        logger.error(f"❌ 事件源错误: {error}")
        self._subject.on_error(error)
    
    async def process_langgraph_events(self, event_stream: AsyncGenerator[Dict[str, Any], None]):
        """
        处理LangGraph事件流
        
        对标TypeScript的processLangGraphEvents逻辑
        """
        self.start()
        
        try:
            async for raw_event in event_stream:
                if not self._running:
                    break
                
                await self._process_single_langgraph_event(raw_event)
        
        except Exception as e:
            logger.error(f"处理LangGraph事件流时出错: {e}")
            self.error(e)
        
        finally:
            self.stop()
    
    async def _process_single_langgraph_event(self, raw_event: Dict[str, Any]):
        """处理单个LangGraph事件"""
        event_type = raw_event.get("event", "")
        data = raw_event.get("data", {})
        
        logger.debug(f"🔄 处理LangGraph事件: {event_type}")
        
        if event_type == LangGraphEventTypes.ON_CHAT_MODEL_STREAM:
            await self._handle_chat_model_stream(data)
        
        elif event_type == LangGraphEventTypes.ON_CHAT_MODEL_START:
            await self._handle_chat_model_start(data)
        
        elif event_type == LangGraphEventTypes.ON_CHAT_MODEL_END:
            await self._handle_chat_model_end(data)
        
        elif event_type == LangGraphEventTypes.ON_TOOL_START:
            await self._handle_tool_start(data)
        
        elif event_type == LangGraphEventTypes.ON_TOOL_END:
            await self._handle_tool_end(data)
        
        elif event_type == LangGraphEventTypes.ON_COPILOTKIT_EMIT_MESSAGE:
            await self._handle_copilotkit_emit_message(data)
        
        elif event_type == LangGraphEventTypes.ON_COPILOTKIT_EMIT_TOOL_CALL:
            await self._handle_copilotkit_emit_tool_call(data)
        
        elif event_type == LangGraphEventTypes.ON_INTERRUPT:
            await self._handle_interrupt(data)
        
        elif event_type == LangGraphEventTypes.ON_COPILOTKIT_INTERRUPT:
            await self._handle_copilotkit_interrupt(data)
        
        else:
            # 其他类型的事件
            await self._handle_custom_event(event_type, data)
    
    async def _handle_chat_model_stream(self, data: Dict[str, Any]):
        """处理聊天模型流事件"""
        chunk = data.get("chunk", {})
        content = chunk.get("content", "")
        
        if content:
            # 如果没有当前消息，创建一个
            if not self._current_message:
                message_id = random_id()
                self._current_message = {
                    "id": message_id,
                    "content": "",
                    "role": MessageRole.ASSISTANT,
                    "type": MessageType.TEXT_MESSAGE
                }
                
                # 发出文本消息开始事件
                self.emit({
                    "type": RuntimeEventTypes.TEXT_MESSAGE_START,
                    "message_id": message_id
                })
            
            # 累积内容
            self._current_message["content"] += content
            
            # 发出文本内容事件
            self.emit({
                "type": RuntimeEventTypes.TEXT_MESSAGE_CONTENT,
                "message_id": self._current_message["id"],
                "content": content
            })
    
    async def _handle_chat_model_start(self, data: Dict[str, Any]):
        """处理聊天模型开始事件"""
        logger.debug("🚀 聊天模型开始")
        # 重置当前消息状态
        self._current_message = None
    
    async def _handle_chat_model_end(self, data: Dict[str, Any]):
        """处理聊天模型结束事件"""
        if self._current_message:
            # 发出文本消息结束事件
            self.emit({
                "type": RuntimeEventTypes.TEXT_MESSAGE_END,
                "message_id": self._current_message["id"]
            })
            
            # 创建完整的文本消息
            message = TextMessage(
                id=self._current_message["id"],
                role=self._current_message["role"],
                content=self._current_message["content"],
                type=self._current_message["type"]
            )
            
            self._message_buffer.append(message)
            logger.debug(f"✅ 完成文本消息: {message.id}")
            
            # 重置当前消息
            self._current_message = None
    
    async def _handle_tool_start(self, data: Dict[str, Any]):
        """处理工具开始事件"""
        tool_name = data.get("name", "")
        tool_input = data.get("input", {})
        run_id = data.get("run_id", random_id())
        
        # 发出动作执行开始事件
        self.emit({
            "type": RuntimeEventTypes.ACTION_EXECUTION_START,
            "action_execution_id": run_id,
            "action_name": tool_name
        })
        
        # 发出动作参数事件
        self.emit({
            "type": RuntimeEventTypes.ACTION_EXECUTION_ARGS,
            "action_execution_id": run_id,
            "args": json.dumps(tool_input)
        })
        
        # 缓存工具调用信息
        self._current_tool_calls[run_id] = {
            "id": run_id,
            "name": tool_name,
            "input": tool_input
        }
        
        logger.debug(f"⚙️ 工具开始: {tool_name}({run_id})")
    
    async def _handle_tool_end(self, data: Dict[str, Any]):
        """处理工具结束事件"""
        run_id = data.get("run_id", "")
        output = data.get("output", "")
        
        if run_id in self._current_tool_calls:
            tool_info = self._current_tool_calls[run_id]
            
            # 发出动作执行结果事件
            self.emit({
                "type": RuntimeEventTypes.ACTION_EXECUTION_RESULT,
                "action_execution_id": run_id,
                "action_name": tool_info["name"],
                "result": json.dumps(output) if not isinstance(output, str) else output
            })
            
            # 发出动作执行结束事件
            self.emit({
                "type": RuntimeEventTypes.ACTION_EXECUTION_END,
                "action_execution_id": run_id
            })
            
            # 创建动作执行和结果消息
            action_message = ActionExecutionMessage(
                id=run_id,
                name=tool_info["name"],
                arguments=tool_info["input"],
                type=MessageType.ACTION_EXECUTION_MESSAGE
            )
            
            result_message = ResultMessage(
                id=random_id(),
                action_execution_id=run_id,
                action_name=tool_info["name"],
                result=json.dumps(output) if not isinstance(output, str) else output,
                type=MessageType.RESULT_MESSAGE
            )
            
            self._message_buffer.extend([action_message, result_message])
            
            # 清理工具调用缓存
            del self._current_tool_calls[run_id]
            
            logger.debug(f"✅ 工具完成: {tool_info['name']}({run_id})")
    
    async def _handle_copilotkit_emit_message(self, data: Dict[str, Any]):
        """处理CopilotKit发出消息事件"""
        message_data = data.get("message", {})
        
        # 根据消息类型创建相应的消息对象
        message_type = message_data.get("type", "text")
        
        if message_type == "text":
            message = TextMessage(
                id=message_data.get("id", random_id()),
                role=MessageRole(message_data.get("role", "assistant")),
                content=message_data.get("content", ""),
                type=MessageType.TEXT_MESSAGE
            )
        else:
            # 其他类型的消息
            return
        
        self._message_buffer.append(message)
        logger.debug(f"📨 CopilotKit消息: {message.id}")
    
    async def _handle_copilotkit_emit_tool_call(self, data: Dict[str, Any]):
        """处理CopilotKit发出工具调用事件"""
        tool_call_data = data.get("tool_call", {})
        
        action_message = ActionExecutionMessage(
            id=tool_call_data.get("id", random_id()),
            name=tool_call_data.get("name", ""),
            arguments=tool_call_data.get("arguments", {}),
            type=MessageType.ACTION_EXECUTION_MESSAGE
        )
        
        self._message_buffer.append(action_message)
        logger.debug(f"🔧 CopilotKit工具调用: {action_message.name}")
    
    async def _handle_interrupt(self, data: Dict[str, Any]):
        """处理中断事件"""
        value = data.get("value", "")
        
        # 发出元事件
        self.emit({
            "type": RuntimeEventTypes.META_EVENT,
            "name": "LangGraphInterruptEvent",
            "value": value
        })
        
        logger.debug(f"⏸️ LangGraph中断: {value}")
    
    async def _handle_copilotkit_interrupt(self, data: Dict[str, Any]):
        """处理CopilotKit中断事件"""
        interrupt_data = {
            "value": data.get("value", ""),
            "messages": self._message_buffer.copy()
        }
        
        # 发出元事件
        self.emit({
            "type": RuntimeEventTypes.META_EVENT,
            "name": "CopilotKitLangGraphInterruptEvent",
            "data": interrupt_data
        })
        
        logger.debug(f"⏸️ CopilotKit中断: {interrupt_data['value']}")
    
    async def _handle_custom_event(self, event_type: str, data: Dict[str, Any]):
        """处理自定义事件"""
        logger.debug(f"🔄 自定义事件: {event_type}")
        
        # 可以在这里添加自定义事件处理逻辑
        pass
    
    def get_messages(self) -> List[Message]:
        """获取缓存的消息"""
        return self._message_buffer.copy()
    
    def clear_messages(self):
        """清空消息缓存"""
        self._message_buffer.clear()
    
    async def to_observable(self) -> rx.Observable:
        """转换为RxPY Observable"""
        return self._subject.pipe(
            ops.take_until(lambda x: x.get("type") == "completed")
        ) 