"""
增强的 CopilotRuntime 实现。

集成了所有增强功能，包括：
- 增强的事件处理系统
- 复杂的中间件管道
- AsyncRepeater 流式处理
- 状态管理和错误处理
- 完全对标 TypeScript 版本
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime

from .copilot_runtime import CopilotRuntime as BaseCopilotRuntime
from ..types.runtime import CopilotRuntimeRequest, CopilotRuntimeResponse, RequestContext
from ..types.adapters import CopilotServiceAdapter, AdapterRequest
from ..types.actions import Action, ActionResult
from ..types.messages import Message, TextMessage, ActionExecutionMessage, ResultMessage
from ..events.enhanced_runtime_events import (
    EnhancedRuntimeEventSource,
    MessageStreamProcessor,
    AsyncRepeater,
    MessageStatus,
    SuccessMessageStatus,
    FailedMessageStatus,
    ResponseStatus
)
from ..middleware.enhanced_middleware import (
    EnhancedMiddlewareChain,
    create_default_middleware_chain,
    MiddlewareResult
)
from ..utils.common import generate_id

logger = logging.getLogger(__name__)


class EnhancedCopilotRuntimeResponse:
    """增强的运行时响应"""
    
    def __init__(self,
                 thread_id: str,
                 run_id: Optional[str] = None,
                 event_source: Optional[EnhancedRuntimeEventSource] = None,
                 server_side_actions: Optional[List[Action]] = None,
                 action_inputs_without_agents: Optional[List[Any]] = None,
                 extensions: Optional[Dict[str, Any]] = None,
                 status: Optional[ResponseStatus] = None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.event_source = event_source
        self.server_side_actions = server_side_actions or []
        self.action_inputs_without_agents = action_inputs_without_agents or []
        self.extensions = extensions or {}
        self.status = status or ResponseStatus("processing")
        
        # 创建消息流处理器
        if self.event_source:
            self.message_processor = MessageStreamProcessor(self.event_source)
        else:
            self.message_processor = None
    
    async def create_message_stream(self) -> AsyncRepeater:
        """创建消息流（类似 TypeScript Repeater）"""
        if not self.message_processor:
            raise ValueError("No event source available for message stream")
        return await self.message_processor.create_message_stream()
    
    async def create_meta_events_stream(self) -> AsyncRepeater:
        """创建元事件流"""
        return AsyncRepeater(self._meta_events_generator)
    
    async def _meta_events_generator(self, push_event, stop_events):
        """元事件生成器"""
        if not self.event_source:
            stop_events()
            return
        
        def meta_event_handler(event):
            if event.type == "meta_event":
                asyncio.create_task(push_event(event.data))
        
        # 订阅元事件
        self.event_source.subscribe("meta_event", meta_event_handler)
        
        # 等待流完成
        while self.event_source._streaming:
            await asyncio.sleep(0.1)
        
        stop_events()


class EnhancedCopilotRuntime:
    """
    增强的 CopilotRuntime
    
    完全对标 TypeScript 版本的功能和架构
    """
    
    def __init__(self,
                 actions: Optional[Union[List[Action], Callable[[Dict[str, Any]], List[Action]]]] = None,
                 agents: Optional[Dict[str, Any]] = None,
                 middleware_chain: Optional[EnhancedMiddlewareChain] = None,
                 remote_endpoints: Optional[List[Any]] = None,
                 delegate_agent_processing: bool = False,
                 **kwargs):
        """
        初始化增强的运行时
        
        Args:
            actions: 动作列表或生成函数
            agents: 代理字典
            middleware_chain: 中间件链
            remote_endpoints: 远程端点
            delegate_agent_processing: 是否委托代理处理
            **kwargs: 其他配置
        """
        self.actions = actions or []
        self.agents = agents or {}
        self.middleware_chain = middleware_chain or create_default_middleware_chain()
        self.remote_endpoints = remote_endpoints or []
        self.delegate_agent_processing = delegate_agent_processing
        
        # 运行时状态
        self._available_agents: List[Any] = []
        self._active_threads: Dict[str, Dict[str, Any]] = {}
        
        logger.info("🚀 Enhanced CopilotRuntime initialized")
    
    async def process_runtime_request(self, request: CopilotRuntimeRequest) -> EnhancedCopilotRuntimeResponse:
        """
        处理运行时请求（增强版本）
        
        Args:
            request: 运行时请求
            
        Returns:
            增强的运行时响应
        """
        thread_id = request.thread_id or generate_id()
        run_id = request.run_id or generate_id()
        
        logger.info(f"🔄 Processing enhanced runtime request - thread_id: {thread_id}, run_id: {run_id}")
        
        try:
            # 创建输出消息 Future（类似 TypeScript 版本）
            output_messages_future = self.middleware_chain.create_output_messages_future(thread_id)
            
            # 创建增强的事件源
            event_source = EnhancedRuntimeEventSource()
            
            # 获取服务端动作
            server_side_actions = await self._get_server_side_actions(request)
            action_inputs_without_agents = [action.to_action_input() for action in server_side_actions]
            
            # 启动中间件处理（异步）
            middleware_task = asyncio.create_task(
                self.middleware_chain.process_request(request, output_messages_future)
            )
            
            # 处理适配器请求
            adapter_task = asyncio.create_task(
                self._process_adapter_request(
                    request, 
                    event_source, 
                    server_side_actions,
                    action_inputs_without_agents,
                    thread_id,
                    run_id,
                    output_messages_future
                )
            )
            
            # 创建响应
            response = EnhancedCopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=event_source,
                server_side_actions=server_side_actions,
                action_inputs_without_agents=action_inputs_without_agents,
                extensions=request.context.properties if request.context else {},
                status=ResponseStatus("processing")
            )
            
            logger.info(f"✅ Enhanced runtime request processed - thread_id: {thread_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced runtime request: {e}")
            
            # 拒绝输出消息 Future
            self.middleware_chain.reject_output_messages(thread_id, e)
            
            # 返回错误响应
            error_event_source = EnhancedRuntimeEventSource()
            await error_event_source.emit({
                "type": "error",
                "data": {
                    "error": str(e),
                    "threadId": thread_id,
                    "code": "RUNTIME_ERROR"
                }
            })
            
            return EnhancedCopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=error_event_source,
                status=ResponseStatus("error", str(e))
            )
    
    async def _process_adapter_request(self,
                                     request: CopilotRuntimeRequest,
                                     event_source: EnhancedRuntimeEventSource,
                                     server_side_actions: List[Action],
                                     action_inputs_without_agents: List[Any],
                                     thread_id: str,
                                     run_id: str,
                                     output_messages_future: asyncio.Future[List[Message]]):
        """
        处理适配器请求（内部方法）
        
        Args:
            request: 运行时请求
            event_source: 事件源
            server_side_actions: 服务端动作
            action_inputs_without_agents: 非代理动作输入
            thread_id: 线程ID
            run_id: 运行ID
            output_messages_future: 输出消息Future
        """
        try:
            # 启动事件流处理
            event_stream_task = asyncio.create_task(
                self._process_event_stream(
                    event_source,
                    server_side_actions,
                    action_inputs_without_agents,
                    thread_id
                )
            )
            
            # 构建适配器请求
            adapter_request = AdapterRequest(
                thread_id=thread_id,
                model=None,  # 由适配器决定
                messages=request.messages,
                actions=action_inputs_without_agents,
                event_source=event_source,
                forwarded_parameters=None
            )
            
            # 调用适配器
            adapter_response = await request.service_adapter.process(adapter_request)
            
            # 等待事件流处理完成
            final_messages = await event_stream_task
            
            # 解析输出消息 Future
            self.middleware_chain.resolve_output_messages(thread_id, final_messages)
            
        except Exception as e:
            logger.error(f"Error in adapter processing: {e}")
            # 拒绝输出消息 Future
            self.middleware_chain.reject_output_messages(thread_id, e)
            raise
    
    async def _process_event_stream(self,
                                  event_source: EnhancedRuntimeEventSource,
                                  server_side_actions: List[Action],
                                  action_inputs_without_agents: List[Any],
                                  thread_id: str) -> List[Message]:
        """
        处理事件流（类似 TypeScript 版本的 processRuntimeEvents）
        
        Args:
            event_source: 事件源
            server_side_actions: 服务端动作
            action_inputs_without_agents: 非代理动作输入
            thread_id: 线程ID
            
        Returns:
            最终消息列表
        """
        output_messages = []
        
        try:
            # 使用增强的事件处理
            async for event in event_source.process_runtime_events(
                server_side_actions=server_side_actions,
                action_inputs_without_agents=action_inputs_without_agents,
                thread_id=thread_id
            ):
                # 处理不同类型的事件
                if event.type == "text_message_end":
                    # 文本消息完成
                    message_id = event.data.get("messageId")
                    if hasattr(event_source.message_processor, 'output_messages'):
                        for msg in event_source.message_processor.output_messages:
                            if msg.id == message_id:
                                output_messages.append(msg)
                                break
                
                elif event.type == "action_execution_result":
                    # 动作执行结果
                    action_execution_id = event.data.get("actionExecutionId")
                    action_name = event.data.get("actionName")
                    result = event.data.get("result")
                    
                    result_message = ResultMessage(
                        id=f"result-{action_execution_id}",
                        action_execution_id=action_execution_id,
                        action_name=action_name,
                        result=result
                    )
                    output_messages.append(result_message)
                
                elif event.type == "error":
                    # 错误处理
                    logger.error(f"Event stream error: {event.data}")
                    break
            
            return output_messages
            
        except Exception as e:
            logger.error(f"Error processing event stream: {e}")
            return output_messages
    
    async def _get_server_side_actions(self, request: CopilotRuntimeRequest) -> List[Action]:
        """
        获取服务端动作
        
        Args:
            request: 运行时请求
            
        Returns:
            动作列表
        """
        if not self.actions:
            return []
        
        # 如果是函数，调用函数获取动作
        if callable(self.actions):
            context = {
                "properties": request.context.properties if request.context else {},
                "url": request.context.url if request.context else None,
                "threadId": request.thread_id,
                "runId": request.run_id
            }
            return self.actions(context)
        
        # 否则直接返回动作列表
        return self.actions
    
    async def execute_action(self, action_name: str, arguments: Dict[str, Any]) -> ActionResult:
        """
        执行动作
        
        Args:
            action_name: 动作名称
            arguments: 动作参数
            
        Returns:
            动作执行结果
        """
        start_time = datetime.now()
        
        try:
            # 查找动作
            action = None
            server_actions = await self._get_server_side_actions(
                CopilotRuntimeRequest(
                    service_adapter=None,
                    messages=[],
                    context=RequestContext()
                )
            )
            
            for a in server_actions:
                if a.name == action_name:
                    action = a
                    break
            
            if not action:
                return ActionResult.error_result(
                    f"Action '{action_name}' not found",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
            
            # 执行动作
            result = await action.execute(arguments)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Action '{action_name}' executed successfully in {execution_time:.3f}s")
            return ActionResult.success_result(result, execution_time)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error executing action '{action_name}': {e}")
            return ActionResult.error_result(str(e), execution_time)
    
    async def get_available_agents(self) -> List[Any]:
        """获取可用的代理列表"""
        return list(self.agents.values())
    
    async def discover_agents_from_endpoints(self) -> List[Any]:
        """从端点发现代理"""
        discovered_agents = []
        
        for endpoint in self.remote_endpoints:
            try:
                # 这里实现代理发现逻辑
                # 具体实现取决于端点类型
                pass
            except Exception as e:
                logger.error(f"Error discovering agents from endpoint: {e}")
        
        return discovered_agents
    
    def add_middleware(self, middleware):
        """添加中间件"""
        self.middleware_chain.add_middleware(middleware)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取运行时指标"""
        metrics = {
            "active_threads": len(self._active_threads),
            "total_actions": len(self.actions) if isinstance(self.actions, list) else 0,
            "total_agents": len(self.agents),
            "total_endpoints": len(self.remote_endpoints)
        }
        
        # 从中间件获取指标
        for middleware in self.middleware_chain.middlewares:
            if hasattr(middleware, 'get_metrics'):
                middleware_metrics = middleware.get_metrics()
                metrics.update(middleware_metrics)
        
        return metrics


# 便捷函数
def create_enhanced_runtime(
    actions: Optional[Union[List[Action], Callable]] = None,
    agents: Optional[Dict[str, Any]] = None,
    use_default_middleware: bool = True,
    api_keys: Optional[List[str]] = None,
    **kwargs
) -> EnhancedCopilotRuntime:
    """
    创建增强的运行时实例
    
    Args:
        actions: 动作列表或生成函数
        agents: 代理字典
        use_default_middleware: 是否使用默认中间件
        api_keys: API密钥列表
        **kwargs: 其他配置
        
    Returns:
        增强的运行时实例
    """
    middleware_chain = None
    if use_default_middleware:
        if api_keys:
            from ..middleware.enhanced_middleware import create_production_middleware_chain
            middleware_chain = create_production_middleware_chain(api_keys)
        else:
            middleware_chain = create_default_middleware_chain()
    
    return EnhancedCopilotRuntime(
        actions=actions,
        agents=agents,
        middleware_chain=middleware_chain,
        **kwargs
    ) 