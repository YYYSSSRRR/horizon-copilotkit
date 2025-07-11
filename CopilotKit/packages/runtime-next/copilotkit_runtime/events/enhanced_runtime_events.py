"""
增强的运行时事件系统实现。

实现了类似 TypeScript 版本的复杂事件处理能力，包括：
- 状态跟踪和自动动作执行
- 事件流式处理
- 错误处理和恢复
- 异步迭代器支持
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncIterator, Callable, Awaitable
from datetime import datetime
from abc import ABC, abstractmethod

from .runtime_events import RuntimeEvent, RuntimeEventSource
from ..types.actions import Action, ActionResult
from ..types.messages import Message, TextMessage, ActionExecutionMessage, ResultMessage, MessageRole

logger = logging.getLogger(__name__)


class MessageStatus:
    """消息状态基类"""
    def __init__(self, code: str, reason: Optional[str] = None):
        self.code = code
        self.reason = reason


class SuccessMessageStatus(MessageStatus):
    """成功状态"""
    def __init__(self):
        super().__init__("success")


class FailedMessageStatus(MessageStatus):
    """失败状态"""
    def __init__(self, reason: str):
        super().__init__("failed", reason)


class ResponseStatus:
    """响应状态"""
    def __init__(self, code: str, description: Optional[str] = None):
        self.code = code
        self.description = description


class CopilotError(Exception):
    """CopilotKit 错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ActionExecutionError(CopilotError):
    """动作执行错误"""
    def __init__(self, action_name: str, error_message: str):
        super().__init__("ACTION_EXECUTION_FAILED", 
                        f"Action '{action_name}' failed: {error_message}")


class AsyncRepeater:
    """
    Python 版本的异步迭代器，类似 TypeScript 的 Repeater
    
    用于实现细粒度的流式控制
    """
    
    def __init__(self, generator_func: Callable):
        self.generator_func = generator_func
        self._queue = asyncio.Queue()
        self._finished = False
        self._task = None
    
    async def start(self, *args, **kwargs):
        """启动生成器"""
        self._task = asyncio.create_task(
            self.generator_func(self._push, self._stop, *args, **kwargs)
        )
    
    async def _push(self, item):
        """推送项目到队列"""
        if not self._finished:
            await self._queue.put(item)
    
    def _stop(self):
        """停止迭代器"""
        self._finished = True
        if self._task and not self._task.done():
            self._task.cancel()
    
    async def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self._finished and self._queue.empty():
            raise StopAsyncIteration
        
        try:
            # 等待项目或超时
            item = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            return item
        except asyncio.TimeoutError:
            if self._finished:
                raise StopAsyncIteration
            # 继续等待
            return await self.__anext__()


class RuntimeEventWithState:
    """带状态的运行时事件"""
    def __init__(self):
        self.event: Optional[RuntimeEvent] = None
        self.call_action_server_side: bool = False
        self.args: str = ""
        self.action_execution_id: Optional[str] = None
        self.action: Optional[Action] = None
        self.action_execution_parent_message_id: Optional[str] = None


class EnhancedRuntimeEventSource(RuntimeEventSource):
    """
    增强的运行时事件源
    
    实现了类似 TypeScript 版本的复杂事件处理能力
    """
    
    def __init__(self):
        super().__init__()
        self._event_state = RuntimeEventWithState()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._interrupt_callbacks: List[Callable] = []
    
    async def process_runtime_events(
        self,
        server_side_actions: List[Action],
        action_inputs_without_agents: List[Any],
        thread_id: str
    ) -> AsyncIterator[RuntimeEvent]:
        """
        处理运行时事件（类似 TypeScript 版本的 processRuntimeEvents）
        
        Args:
            server_side_actions: 服务器端动作列表
            action_inputs_without_agents: 非代理动作输入
            thread_id: 线程ID
            
        Yields:
            处理后的运行时事件
        """
        try:
            async for event in self._event_stream():
                # 更新事件状态
                updated_state = self._update_event_state(event, server_side_actions)
                
                # 检查是否需要执行动作
                if (event.type == "action_execution_end" and 
                    updated_state.call_action_server_side):
                    
                    # 先发送原始事件
                    yield event
                    
                    # 执行动作并发送结果事件
                    async for result_event in self._execute_action(
                        updated_state.action,
                        updated_state.args,
                        updated_state.action_execution_parent_message_id,
                        updated_state.action_execution_id,
                        action_inputs_without_agents,
                        thread_id
                    ):
                        yield result_event
                else:
                    # 发送普通事件
                    yield event
                    
        except Exception as e:
            logger.error(f"Error in process_runtime_events: {e}")
            # 发送错误事件
            yield RuntimeEvent(
                type="error",
                data={
                    "error": str(e),
                    "threadId": thread_id,
                    "code": "RUNTIME_EVENT_PROCESSING_ERROR"
                }
            )
    
    def _update_event_state(
        self, 
        event: RuntimeEvent, 
        server_side_actions: List[Action]
    ) -> RuntimeEventWithState:
        """
        更新事件状态（类似 TypeScript 版本的 scan 操作）
        
        Args:
            event: 当前事件
            server_side_actions: 服务器端动作列表
            
        Returns:
            更新后的事件状态
        """
        # 复制当前状态以避免副作用
        state = RuntimeEventWithState()
        state.event = event
        state.call_action_server_side = self._event_state.call_action_server_side
        state.args = self._event_state.args
        state.action_execution_id = self._event_state.action_execution_id
        state.action = self._event_state.action
        state.action_execution_parent_message_id = self._event_state.action_execution_parent_message_id
        
        if event.type == "action_execution_start":
            action_name = event.data.get("actionName")
            state.call_action_server_side = any(
                action.name == action_name for action in server_side_actions
            )
            state.args = ""
            state.action_execution_id = event.data.get("actionExecutionId")
            if state.call_action_server_side:
                state.action = next(
                    (action for action in server_side_actions if action.name == action_name),
                    None
                )
            state.action_execution_parent_message_id = event.data.get("parentMessageId")
            
        elif event.type == "action_execution_args":
            state.args += event.data.get("args", "")
        
        # 更新内部状态
        self._event_state = state
        return state
    
    async def _execute_action(
        self,
        action: Optional[Action],
        action_arguments: str,
        action_execution_parent_message_id: Optional[str],
        action_execution_id: Optional[str],
        action_inputs_without_agents: List[Any],
        thread_id: str
    ) -> AsyncIterator[RuntimeEvent]:
        """
        执行动作（类似 TypeScript 版本的 executeAction）
        
        Args:
            action: 要执行的动作
            action_arguments: 动作参数（JSON字符串）
            action_execution_parent_message_id: 父消息ID
            action_execution_id: 动作执行ID
            action_inputs_without_agents: 非代理动作输入
            thread_id: 线程ID
            
        Yields:
            动作执行结果事件
        """
        if not action:
            yield RuntimeEvent(
                type="action_execution_result",
                data={
                    "actionExecutionId": action_execution_id,
                    "actionName": "unknown",
                    "error": {
                        "code": "ACTION_NOT_FOUND",
                        "message": "Action not found"
                    },
                    "success": False
                }
            )
            return
        
        # 解析参数
        args = {}
        if action_arguments:
            try:
                args = json.loads(action_arguments)
            except json.JSONDecodeError:
                logger.error(f"Action argument unparsable: {action_arguments}")
                yield RuntimeEvent(
                    type="action_execution_result",
                    data={
                        "actionExecutionId": action_execution_id,
                        "actionName": action.name,
                        "error": {
                            "code": "INVALID_ARGUMENTS",
                            "message": "Failed to parse action arguments"
                        },
                        "success": False
                    }
                )
                return
        
        # 执行动作
        try:
            result = await action.execute(args)
            
            # 发送成功结果
            yield RuntimeEvent(
                type="action_execution_result",
                data={
                    "actionExecutionId": action_execution_id,
                    "actionName": action.name,
                    "result": result,
                    "success": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error in action handler: {e}")
            
            # 发送错误结果
            yield RuntimeEvent(
                type="action_execution_result",
                data={
                    "actionExecutionId": action_execution_id,
                    "actionName": action.name,
                    "error": {
                        "code": "HANDLER_ERROR",
                        "message": str(e)
                    },
                    "success": False
                }
            )
    
    async def _event_stream(self) -> AsyncIterator[RuntimeEvent]:
        """内部事件流迭代器"""
        while self._streaming:
            if self._events:
                # 发送已有事件
                for event in self._events:
                    yield event
                self._events.clear()
            
            # 短暂等待新事件
            await asyncio.sleep(0.01)
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅特定类型的事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass
    
    async def emit(self, event: RuntimeEvent) -> None:
        """发射事件（覆盖父类方法以添加订阅者通知）"""
        await super().emit(event)
        
        # 通知订阅者
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}")
    
    def add_interrupt_callback(self, callback: Callable):
        """添加中断回调"""
        self._interrupt_callbacks.append(callback)
    
    async def interrupt_streaming(self, reason: str, message_id: Optional[str] = None):
        """中断流式传输"""
        for callback in self._interrupt_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"reason": reason, "messageId": message_id})
                else:
                    callback({"reason": reason, "messageId": message_id})
            except Exception as e:
                logger.error(f"Error in interrupt callback: {e}")


class MessageStreamProcessor:
    """
    消息流处理器
    
    实现类似 TypeScript Resolver 的消息流式处理能力
    """
    
    def __init__(self, event_source: EnhancedRuntimeEventSource):
        self.event_source = event_source
        self.output_messages: List[Message] = []
    
    async def create_message_stream(self) -> AsyncRepeater:
        """创建消息流"""
        return AsyncRepeater(self._message_generator)
    
    async def _message_generator(self, push_message, stop_streaming):
        """消息生成器"""
        try:
            # 订阅相关事件
            self.event_source.subscribe("text_message_start", 
                                       lambda e: self._handle_text_message_start(e, push_message))
            self.event_source.subscribe("action_execution_start", 
                                       lambda e: self._handle_action_execution_start(e, push_message))
            self.event_source.subscribe("action_execution_result", 
                                       lambda e: self._handle_action_execution_result(e, push_message))
            
            # 等待流完成
            while self.event_source._streaming:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in message generator: {e}")
        finally:
            stop_streaming()
    
    async def _handle_text_message_start(self, event: RuntimeEvent, push_message):
        """处理文本消息开始事件"""
        message_id = event.data.get("messageId")
        parent_message_id = event.data.get("parentMessageId")
        
        # 创建文本内容流
        content_stream = AsyncRepeater(self._text_content_generator)
        await content_stream.start(message_id)
        
        # 推送消息
        await push_message({
            "id": message_id,
            "parentMessageId": parent_message_id,
            "role": MessageRole.ASSISTANT,
            "content": content_stream,
            "status": SuccessMessageStatus(),
            "createdAt": datetime.now()
        })
    
    async def _text_content_generator(self, push_content, stop_content, message_id):
        """文本内容生成器"""
        text_chunks = []
        
        def content_handler(event: RuntimeEvent):
            if (event.type == "text_message_content" and 
                event.data.get("messageId") == message_id):
                content = event.data.get("content", "")
                text_chunks.append(content)
                asyncio.create_task(push_content(content))
        
        def end_handler(event: RuntimeEvent):
            if (event.type == "text_message_end" and 
                event.data.get("messageId") == message_id):
                # 添加到输出消息
                self.output_messages.append(TextMessage(
                    id=message_id,
                    content="".join(text_chunks),
                    role=MessageRole.ASSISTANT
                ))
                stop_content()
        
        # 订阅事件
        self.event_source.subscribe("text_message_content", content_handler)
        self.event_source.subscribe("text_message_end", end_handler)
        
        # 等待完成
        while not stop_content._finished:
            await asyncio.sleep(0.01)
    
    async def _handle_action_execution_start(self, event: RuntimeEvent, push_message):
        """处理动作执行开始事件"""
        action_execution_id = event.data.get("actionExecutionId")
        action_name = event.data.get("actionName")
        parent_message_id = event.data.get("parentMessageId")
        
        # 创建参数流
        arguments_stream = AsyncRepeater(self._action_arguments_generator)
        await arguments_stream.start(action_execution_id)
        
        # 推送动作执行消息
        await push_message({
            "id": action_execution_id,
            "parentMessageId": parent_message_id,
            "name": action_name,
            "arguments": arguments_stream,
            "status": SuccessMessageStatus(),
            "createdAt": datetime.now()
        })
    
    async def _action_arguments_generator(self, push_args, stop_args, action_execution_id):
        """动作参数生成器"""
        argument_chunks = []
        
        def args_handler(event: RuntimeEvent):
            if (event.type == "action_execution_args" and 
                event.data.get("actionExecutionId") == action_execution_id):
                args = event.data.get("args", "")
                argument_chunks.append(args)
                asyncio.create_task(push_args(args))
        
        def end_handler(event: RuntimeEvent):
            if (event.type == "action_execution_end" and 
                event.data.get("actionExecutionId") == action_execution_id):
                # 添加到输出消息
                self.output_messages.append(ActionExecutionMessage(
                    id=action_execution_id,
                    name=event.data.get("actionName", ""),
                    arguments="".join(argument_chunks)
                ))
                stop_args()
        
        # 订阅事件
        self.event_source.subscribe("action_execution_args", args_handler)
        self.event_source.subscribe("action_execution_end", end_handler)
        
        # 等待完成
        while not stop_args._finished:
            await asyncio.sleep(0.01)
    
    async def _handle_action_execution_result(self, event: RuntimeEvent, push_message):
        """处理动作执行结果事件"""
        action_execution_id = event.data.get("actionExecutionId")
        action_name = event.data.get("actionName")
        result = event.data.get("result")
        
        # 推送结果消息
        await push_message({
            "id": f"result-{action_execution_id}",
            "actionExecutionId": action_execution_id,
            "actionName": action_name,
            "result": result,
            "status": SuccessMessageStatus(),
            "createdAt": datetime.now()
        })
        
        # 添加到输出消息
        self.output_messages.append(ResultMessage(
            id=f"result-{action_execution_id}",
            action_execution_id=action_execution_id,
            action_name=action_name,
            result=result
        )) 