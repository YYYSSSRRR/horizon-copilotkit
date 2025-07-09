"""
CopilotRuntime核心实现。
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic, cast
import time

from ..types.adapters import CopilotServiceAdapter, EmptyAdapter
from ..types.runtime import (
    CopilotRuntimeRequest, 
    CopilotRuntimeResponse, 
    OnBeforeRequestHandler,
    OnAfterRequestHandler,
    Middleware,
    RequestContext
)
from ..types.actions import (
    Action, 
    Parameter, 
    ActionResult, 
    ActionAvailability
)
from ..types.messages import (
    Message, 
    TextMessage, 
    MessageRole, 
    MessageType,
    ActionExecutionMessage,
    ResultMessage
)
from ..types.agents import (
    Agent, 
    AgentWithEndpoint, 
    AgentState
)
from ..types.endpoints import (
    EndpointDefinition,
    CopilotKitEndpoint,
    LangGraphEndpoint,
    EndpointType
)
from ..events.runtime_events import RuntimeEventSource, RuntimeEvent
from ..utils.common import generate_id


logger = logging.getLogger(__name__)


T = TypeVar('T', bound=List[Parameter])


class CopilotRuntime(Generic[T]):
    """
    CopilotKit运行时
    
    负责处理请求、执行动作、管理代理等。
    """
    
    def __init__(
        self,
        middleware: Optional[Middleware] = None,
        actions: Optional[Union[List[Action], Callable[[Dict[str, Any]], List[Action]]]] = None,
        remote_endpoints: Optional[List[EndpointDefinition]] = None,
        delegate_agent_processing_to_service_adapter: bool = False,
        agents: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化CopilotRuntime
        
        Args:
            middleware: 中间件
            actions: 服务器端动作列表或生成函数
            remote_endpoints: 远程端点列表
            delegate_agent_processing_to_service_adapter: 是否将代理处理委托给服务适配器
            agents: 代理映射
        """
        # 初始化中间件
        self.on_before_request = middleware.on_before_request if middleware else None
        self.on_after_request = middleware.on_after_request if middleware else None
        
        # 初始化动作
        self.actions = actions or []
        
        # 初始化远程端点
        self.remote_endpoint_definitions = remote_endpoints or []
        
        # 初始化代理设置
        self.delegate_agent_processing_to_service_adapter = delegate_agent_processing_to_service_adapter
        self.agents = agents or {}
        
        # 初始化缓存
        self.available_agents: List[Agent] = []
        
        logger.info(f"CopilotRuntime initialized with {len(self.remote_endpoint_definitions)} remote endpoints")
    
    async def process_runtime_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """
        处理运行时请求
        
        Args:
            request: 运行时请求
            
        Returns:
            运行时响应
        """
        # 生成线程ID和运行ID（如果未提供）
        thread_id = request.thread_id or generate_id()
        run_id = request.run_id or generate_id()
        
        # 创建事件源
        event_source = RuntimeEventSource()
        
        try:
            # 准备输入消息
            input_messages = request.messages
            
            # 调用前置中间件
            if self.on_before_request:
                await self._call_on_before_request(
                    thread_id=thread_id,
                    run_id=run_id,
                    input_messages=input_messages,
                    properties=request.context.properties if request.context else {},
                    url=request.context.url if request.context else None
                )
            
            # 处理代理请求
            if request.agent_session:
                return await self._process_agent_request(request)
            
            # 获取服务器端动作
            server_side_actions = await self._get_server_side_actions(request)
            
            # 调用服务适配器
            output_messages_future = asyncio.create_task(
                self._call_service_adapter(
                    adapter=request.service_adapter,
                    messages=input_messages,
                    actions=server_side_actions,
                    event_source=event_source,
                    thread_id=thread_id,
                    run_id=run_id
                )
            )
            
            # 调用后置中间件
            if self.on_after_request:
                output_messages_future.add_done_callback(
                    lambda f: asyncio.create_task(
                        self._call_on_after_request(
                            thread_id=thread_id,
                            run_id=run_id,
                            input_messages=input_messages,
                            output_messages=f.result(),
                            properties=request.context.properties if request.context else {},
                            url=request.context.url if request.context else None
                        )
                    )
                )
            
            return CopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=event_source,
                server_side_actions=server_side_actions
            )
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            # 发送错误事件
            event_source.emit(RuntimeEvent(
                type="error",
                data={"error": str(e), "threadId": thread_id}
            ))
            # 返回错误响应
            return CopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=event_source,
                server_side_actions=[]
            )
    
    async def _process_agent_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """
        处理代理请求
        
        Args:
            request: 运行时请求
            
        Returns:
            运行时响应
        """
        agent_session = request.agent_session
        if not agent_session:
            raise ValueError("Agent session is required for agent requests")
        
        agent_name = agent_session.agent_name
        thread_id = request.thread_id or agent_session.thread_id or generate_id()
        run_id = request.run_id or generate_id()
        
        # 创建事件源
        event_source = RuntimeEventSource()
        
        # 如果委托给服务适配器
        if self.delegate_agent_processing_to_service_adapter:
            # 获取服务器端动作
            server_side_actions = await self._get_server_side_actions(request)
            
            # 调用服务适配器
            output_messages_future = asyncio.create_task(
                self._call_service_adapter(
                    adapter=request.service_adapter,
                    messages=request.messages,
                    actions=server_side_actions,
                    event_source=event_source,
                    thread_id=thread_id,
                    run_id=run_id,
                    agent_session=agent_session
                )
            )
            
            return CopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=event_source,
                server_side_actions=server_side_actions
            )
        
        # 查找代理
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        # 获取代理状态
        agent_state = await self.load_agent_state(agent_name, thread_id)
        
        # 调用代理
        try:
            # 这里实现代理调用逻辑
            # 由于Python版本不依赖于AGUI，我们需要实现自己的代理调用逻辑
            # 这部分可以根据具体需求实现
            pass
            
        except Exception as e:
            logger.error(f"Error processing agent request: {e}")
            event_source.emit(RuntimeEvent(
                type="error",
                data={"error": str(e), "threadId": thread_id, "agentName": agent_name}
            ))
        
        return CopilotRuntimeResponse(
            thread_id=thread_id,
            run_id=run_id,
            event_source=event_source,
            server_side_actions=[]
        )
    
    async def _call_service_adapter(
        self,
        adapter: CopilotServiceAdapter,
        messages: List[Message],
        actions: List[Action],
        event_source: RuntimeEventSource,
        thread_id: str,
        run_id: str,
        agent_session: Optional[Any] = None
    ) -> List[Message]:
        """
        调用服务适配器
        
        Args:
            adapter: 服务适配器
            messages: 输入消息
            actions: 可用动作
            event_source: 事件源
            thread_id: 线程ID
            run_id: 运行ID
            agent_session: 代理会话
            
        Returns:
            输出消息列表
        """
        try:
            # 检测适配器类型
            provider = self._detect_provider(adapter)
            
            # 发送会话开始事件
            event_source.emit(RuntimeEvent(
                type="session_start",
                data={
                    "threadId": thread_id,
                    "runId": run_id,
                    "provider": provider
                }
            ))
            
            # 调用适配器
            response_messages = await adapter.process_messages(
                messages=messages,
                actions=actions,
                event_source=event_source,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # 发送会话结束事件
            event_source.emit(RuntimeEvent(
                type="session_end",
                data={
                    "threadId": thread_id,
                    "runId": run_id
                }
            ))
            
            return response_messages
            
        except Exception as e:
            logger.error(f"Error calling service adapter: {e}")
            event_source.emit(RuntimeEvent(
                type="error",
                data={"error": str(e), "threadId": thread_id}
            ))
            return []
    
    async def _get_server_side_actions(self, request: CopilotRuntimeRequest) -> List[Action]:
        """
        获取服务器端动作
        
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
                "url": request.context.url if request.context else None
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
        # 获取所有动作
        all_actions = self.actions if isinstance(self.actions, list) else self.actions({"properties": {}})
        
        # 查找动作
        action = next((a for a in all_actions if a.name == action_name), None)
        if not action:
            return ActionResult(
                success=False,
                error=f"Action '{action_name}' not found"
            )
        
        # 执行动作
        try:
            start_time = time.time()
            
            # 调用处理函数
            result = await self._call_action_handler(action, arguments)
            
            execution_time = time.time() - start_time
            
            return ActionResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error executing action '{action_name}': {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )
    
    async def _call_action_handler(self, action: Action, arguments: Dict[str, Any]) -> Any:
        """
        调用动作处理函数
        
        Args:
            action: 动作
            arguments: 参数
            
        Returns:
            处理结果
        """
        if not action.handler:
            raise ValueError(f"Action '{action.name}' has no handler")
        
        # 检查处理函数是否为协程函数
        if inspect.iscoroutinefunction(action.handler):
            return await action.handler(**arguments)
        else:
            return action.handler(**arguments)
    
    async def _call_on_before_request(
        self,
        thread_id: Optional[str],
        run_id: Optional[str],
        input_messages: List[Message],
        properties: Dict[str, Any],
        url: Optional[str]
    ) -> None:
        """
        调用前置请求处理器
        
        Args:
            thread_id: 线程ID
            run_id: 运行ID
            input_messages: 输入消息
            properties: 属性
            url: URL
        """
        if not self.on_before_request:
            return
        
        try:
            options = {
                "threadId": thread_id,
                "runId": run_id,
                "inputMessages": input_messages,
                "properties": properties,
                "url": url
            }
            
            # 调用处理函数
            result = self.on_before_request(options)
            
            # 如果是协程，等待完成
            if asyncio.iscoroutine(result):
                await result
                
        except Exception as e:
            logger.error(f"Error in onBeforeRequest: {e}")
    
    async def _call_on_after_request(
        self,
        thread_id: str,
        run_id: Optional[str],
        input_messages: List[Message],
        output_messages: List[Message],
        properties: Dict[str, Any],
        url: Optional[str]
    ) -> None:
        """
        调用后置请求处理器
        
        Args:
            thread_id: 线程ID
            run_id: 运行ID
            input_messages: 输入消息
            output_messages: 输出消息
            properties: 属性
            url: URL
        """
        if not self.on_after_request:
            return
        
        try:
            options = {
                "threadId": thread_id,
                "runId": run_id,
                "inputMessages": input_messages,
                "outputMessages": output_messages,
                "properties": properties,
                "url": url
            }
            
            # 调用处理函数
            result = self.on_after_request(options)
            
            # 如果是协程，等待完成
            if asyncio.iscoroutine(result):
                await result
                
        except Exception as e:
            logger.error(f"Error in onAfterRequest: {e}")
    
    async def get_available_agents(self) -> List[Agent]:
        """
        获取可用代理
        
        Returns:
            代理列表
        """
        # 如果已经有缓存，直接返回
        if self.available_agents:
            return self.available_agents
        
        # 收集本地代理
        local_agents = [
            Agent(
                name=name,
                id=name,
                description=getattr(agent, "description", None)
            )
            for name, agent in self.agents.items()
        ]
        
        # 从远程端点发现代理
        remote_agents = await self._discover_agents_from_endpoints()
        
        # 合并代理列表
        self.available_agents = local_agents + remote_agents
        
        return self.available_agents
    
    async def _discover_agents_from_endpoints(self) -> List[Agent]:
        """
        从端点发现代理
        
        Returns:
            代理列表
        """
        agents = []
        
        # 遍历远程端点
        for endpoint in self.remote_endpoint_definitions:
            try:
                # 根据端点类型处理
                if endpoint.type == EndpointType.COPILOT_KIT:
                    # 调用CopilotKit端点
                    pass
                elif endpoint.type == EndpointType.LANG_GRAPH:
                    # 调用LangGraph端点
                    pass
                
            except Exception as e:
                logger.error(f"Error discovering agents from endpoint {endpoint.url}: {e}")
        
        return agents
    
    async def load_agent_state(self, agent_name: str, thread_id: str) -> Optional[AgentState]:
        """
        加载代理状态
        
        Args:
            agent_name: 代理名称
            thread_id: 线程ID
            
        Returns:
            代理状态
        """
        # 查找本地代理
        agent = self.agents.get(agent_name)
        if agent:
            # 如果代理有load_state方法，调用它
            if hasattr(agent, "load_state") and callable(agent.load_state):
                try:
                    state = await agent.load_state(thread_id) if inspect.iscoroutinefunction(agent.load_state) else agent.load_state(thread_id)
                    return AgentState(
                        agent_name=agent_name,
                        thread_id=thread_id,
                        state=state,
                        running=True,
                        active=True
                    )
                except Exception as e:
                    logger.error(f"Error loading state for agent '{agent_name}': {e}")
        
        # 从远程端点加载状态
        for endpoint in self.remote_endpoint_definitions:
            # 查找匹配的代理端点
            pass
        
        return None
    
    async def save_agent_state(self, agent_name: str, thread_id: str, state: Any) -> None:
        """
        保存代理状态
        
        Args:
            agent_name: 代理名称
            thread_id: 线程ID
            state: 状态
        """
        # 查找本地代理
        agent = self.agents.get(agent_name)
        if agent:
            # 如果代理有save_state方法，调用它
            if hasattr(agent, "save_state") and callable(agent.save_state):
                try:
                    if inspect.iscoroutinefunction(agent.save_state):
                        await agent.save_state(thread_id, state)
                    else:
                        agent.save_state(thread_id, state)
                    return
                except Exception as e:
                    logger.error(f"Error saving state for agent '{agent_name}': {e}")
        
        # 保存到远程端点
        for endpoint in self.remote_endpoint_definitions:
            # 查找匹配的代理端点
            pass
    
    def _detect_provider(self, service_adapter: CopilotServiceAdapter) -> Optional[str]:
        """
        检测服务提供商
        
        Args:
            service_adapter: 服务适配器
            
        Returns:
            提供商名称
        """
        if isinstance(service_adapter, EmptyAdapter):
            return None
        
        # 获取提供商名称
        if hasattr(service_adapter, "get_provider_name"):
            return service_adapter.get_provider_name()
        
        # 尝试从类名推断
        adapter_class = service_adapter.__class__.__name__
        if "OpenAI" in adapter_class:
            return "openai"
        elif "DeepSeek" in adapter_class:
            return "deepseek"
        
        return None


def copilot_kit_endpoint(config: Dict[str, Any]) -> CopilotKitEndpoint:
    """
    创建CopilotKit端点
    
    Args:
        config: 端点配置
        
    Returns:
        CopilotKit端点
    """
    return CopilotKitEndpoint(
        type=EndpointType.COPILOT_KIT,
        **config
    )


def lang_graph_endpoint(config: Dict[str, Any]) -> LangGraphEndpoint:
    """
    创建LangGraph端点
    
    Args:
        config: 端点配置
        
    Returns:
        LangGraph端点
    """
    return LangGraphEndpoint(
        type=EndpointType.LANG_GRAPH,
        **config
    ) 