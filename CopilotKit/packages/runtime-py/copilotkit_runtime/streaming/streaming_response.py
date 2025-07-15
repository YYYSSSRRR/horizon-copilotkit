"""
流式响应处理

使用RxPY实现流式响应，对标TypeScript的RxJS实现
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime

import reactivex as rx
from reactivex import operators as ops
from pydantic import BaseModel

from ..types.messages import (
    Message,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage
)
from ..types.enums import (
    RuntimeEventTypes,
    MessageRole,
    MessageType
)
from ..types.events import RuntimeEvent
from ..utils import random_id

logger = logging.getLogger(__name__)


class StreamingResponse:
    """
    流式响应处理器
    
    对标TypeScript的Repeater和Observable
    """
    
    def __init__(self):
        self._subject = rx.subject.ReplaySubject(buffer_size=1000)
        self._observers = []
        self._completed = False
        self._error = None
    
    def subscribe(self, observer):
        """订阅流"""
        self._observers.append(observer)
        return self._subject.subscribe(observer)
    
    def push(self, item: Any):
        """推送项目到流中"""
        if not self._completed:
            self._subject.on_next(item)
    
    def push_message(self, message: Message):
        """推送消息"""
        logger.debug(f"📤 推送消息: {message.type}, id={message.id}")
        self.push(message)
    
    def push_text_chunk(self, message_id: str, content: str):
        """推送文本块"""
        self.push({
            "type": "text_chunk",
            "message_id": message_id,
            "content": content,
            "timestamp": datetime.utcnow()
        })
    
    def push_event(self, event: RuntimeEvent):
        """推送事件"""
        logger.debug(f"📤 推送事件: {event.type}")
        self.push(event)
    
    def complete(self):
        """完成流"""
        if not self._completed:
            self._completed = True
            self._subject.on_completed()
            logger.debug("✅ 流式响应完成")
    
    def error(self, error: Exception):
        """推送错误"""
        if not self._completed:
            self._error = error
            self._subject.on_error(error)
            logger.error(f"❌ 流式响应错误: {error}")
    
    async def to_list(self) -> List[Any]:
        """将流转换为列表"""
        items = []
        
        def on_next(item):
            items.append(item)
        
        def on_error(error):
            logger.error(f"流转换错误: {error}")
        
        def on_completed():
            logger.debug("流转换完成")
        
        self._subject.subscribe(
            on_next=on_next,
            on_error=on_error,
            on_completed=on_completed
        )
        
        # 等待流完成
        while not self._completed and not self._error:
            await asyncio.sleep(0.01)
        
        if self._error:
            raise self._error
        
        return items
    
    async def to_async_generator(self) -> AsyncGenerator[Any, None]:
        """将流转换为异步生成器"""
        queue = asyncio.Queue()
        completed = False
        error = None
        
        def on_next(item):
            asyncio.create_task(queue.put(item))
        
        def on_error(err):
            nonlocal error
            error = err
            asyncio.create_task(queue.put(None))  # 结束信号
        
        def on_completed():
            nonlocal completed
            completed = True
            asyncio.create_task(queue.put(None))  # 结束信号
        
        self._subject.subscribe(
            on_next=on_next,
            on_error=on_error,
            on_completed=on_completed
        )
        
        while True:
            try:
                item = await queue.get()
                if item is None:  # 结束信号
                    break
                yield item
            except Exception as e:
                logger.error(f"异步生成器错误: {e}")
                break
        
        if error:
            raise error


class MessageStreamer:
    """
    消息流处理器
    
    对标TypeScript的copilot.resolver.ts中的消息流逻辑
    """
    
    def __init__(self):
        self.response = StreamingResponse()
        self._current_message_id = None
        self._current_content = ""
    
    def start_text_message(self, message_id: Optional[str] = None, parent_message_id: Optional[str] = None) -> str:
        """开始文本消息"""
        message_id = message_id or random_id()
        self._current_message_id = message_id
        self._current_content = ""
        
        # 推送文本消息开始事件
        event = {
            "type": RuntimeEventTypes.TEXT_MESSAGE_START,
            "message_id": message_id,
            "parent_message_id": parent_message_id
        }
        self.response.push_event(event)
        
        logger.debug(f"🚀 开始文本消息: {message_id}")
        return message_id
    
    def push_text_content(self, content: str):
        """推送文本内容"""
        if self._current_message_id:
            self._current_content += content
            
            # 推送文本内容事件
            event = {
                "type": RuntimeEventTypes.TEXT_MESSAGE_CONTENT,
                "message_id": self._current_message_id,
                "content": content
            }
            self.response.push_event(event)
            self.response.push_text_chunk(self._current_message_id, content)
            
            logger.debug(f"📝 推送文本内容: {content[:50]}...")
    
    def end_text_message(self) -> Optional[TextMessage]:
        """结束文本消息"""
        if self._current_message_id and self._current_content:
            message = TextMessage(
                id=self._current_message_id,
                role=MessageRole.ASSISTANT,
                content=self._current_content,
                type=MessageType.TEXT_MESSAGE
            )
            
            # 推送文本消息结束事件
            event = {
                "type": RuntimeEventTypes.TEXT_MESSAGE_END,
                "message_id": self._current_message_id
            }
            self.response.push_event(event)
            self.response.push_message(message)
            
            logger.debug(f"✅ 完成文本消息: {self._current_message_id}")
            
            # 重置状态
            self._current_message_id = None
            self._current_content = ""
            
            return message
        
        return None
    
    def push_action_execution(self, action_execution_id: str, action_name: str, args: Dict[str, Any]):
        """推送动作执行"""
        # 推送动作执行开始事件
        start_event = {
            "type": RuntimeEventTypes.ACTION_EXECUTION_START,
            "action_execution_id": action_execution_id,
            "action_name": action_name
        }
        self.response.push_event(start_event)
        
        # 推送动作参数事件
        args_event = {
            "type": RuntimeEventTypes.ACTION_EXECUTION_ARGS,
            "action_execution_id": action_execution_id,
            "args": json.dumps(args)
        }
        self.response.push_event(args_event)
        
        # 创建动作执行消息
        message = ActionExecutionMessage(
            id=action_execution_id,
            name=action_name,
            arguments=args,
            type=MessageType.ACTION_EXECUTION_MESSAGE
        )
        self.response.push_message(message)
        
        logger.debug(f"⚙️ 推送动作执行: {action_name}({action_execution_id})")
    
    def push_action_result(self, action_execution_id: str, action_name: str, result: str):
        """推送动作结果"""
        # 推送动作结果事件
        result_event = {
            "type": RuntimeEventTypes.ACTION_EXECUTION_RESULT,
            "action_execution_id": action_execution_id,
            "action_name": action_name,
            "result": result
        }
        self.response.push_event(result_event)
        
        # 推送动作执行结束事件
        end_event = {
            "type": RuntimeEventTypes.ACTION_EXECUTION_END,
            "action_execution_id": action_execution_id
        }
        self.response.push_event(end_event)
        
        # 创建结果消息
        message = ResultMessage(
            id=random_id(),
            action_execution_id=action_execution_id,
            action_name=action_name,
            result=result,
            type=MessageType.RESULT_MESSAGE
        )
        self.response.push_message(message)
        
        logger.debug(f"✅ 推送动作结果: {action_name}({action_execution_id})")
    
    def complete(self):
        """完成流"""
        self.response.complete()
    
    def error(self, error: Exception):
        """推送错误"""
        self.response.error(error) 