"""
CopilotKit 运行时核心实现。
"""

from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import logging
from datetime import datetime

from .types.runtime import CopilotRuntimeRequest, CopilotRuntimeResponse, RequestContext
from .types.adapters import CopilotServiceAdapter, AdapterRequest
from .types.actions import Action, ActionInput, ActionResult
from .types.messages import Message, TextMessage, ActionExecutionMessage, ResultMessage
from .types.middleware import Middleware, BeforeRequestOptions, AfterRequestOptions
from .types.agents import Agent, AgentState, AgentSession
from .events.runtime_events import RuntimeEventSource
from .utils.common import generate_id

logger = logging.getLogger(__name__)


class CopilotRuntime:
    """
    CopilotKit 运行时核心类
    
    负责：
    - 管理动作和代理
    - 处理请求和响应
    - 中间件执行
    - 事件流处理
    """
    
    def __init__(
        self,
        actions: Optional[Union[List[Action], Callable[[Dict[str, Any]], List[Action]]]] = None,
        agents: Optional[Dict[str, Agent]] = None,
        middleware: Optional[Middleware] = None,
        **kwargs
    ):
        """
        初始化运行时
        
        Args:
            actions: 动作列表或动作生成函数
            agents: 代理字典
            middleware: 中间件配置
            **kwargs: 其他配置参数
        """
        self.actions = actions or []
        self.agents = agents or {}
        self.middleware = middleware
        
        # 运行时状态
        self._available_agents: List[Agent] = []
        
        logger.info("CopilotRuntime initialized")
    
    async def process_runtime_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """
        处理运行时请求
        
        Args:
            request: 运行时请求
            
        Returns:
            运行时响应
        """
        thread_id = request.thread_id or generate_id()
        run_id = request.run_id or generate_id()
        
        logger.info(f"🔄 Processing runtime request - thread_id: {thread_id}, run_id: {run_id}")
        
        try:
            # 执行请求前中间件
            if self.middleware and self.middleware.on_before_request:
                before_options = BeforeRequestOptions(
                    thread_id=thread_id,
                    run_id=run_id,
                    input_messages=request.messages,
                    properties=request.context.properties,
                    url=request.context.url
                )
                
                if asyncio.iscoroutinefunction(self.middleware.on_before_request):
                    await self.middleware.on_before_request(before_options)
                else:
                    self.middleware.on_before_request(before_options)
            
            # 获取服务端动作
            server_side_actions = await self._get_server_side_actions(request)
            
            # 准备动作输入（排除代理动作）
            action_inputs_without_agents = [action.to_action_input() for action in server_side_actions]
            
            # 创建事件源
            event_source = RuntimeEventSource()
            
            # 构建适配器请求
            adapter_request = AdapterRequest(
                thread_id=thread_id,
                model=None,  # 由适配器决定
                messages=request.messages,
                actions=action_inputs_without_agents,
                event_source=event_source,
                forwarded_parameters=None  # 可以根据需要添加
            )
            
            # 处理适配器请求
            adapter_response = await request.service_adapter.process(adapter_request)
            
            # 创建响应
            response = CopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=run_id,
                event_source=adapter_response.event_source,
                server_side_actions=server_side_actions,
                action_inputs_without_agents=action_inputs_without_agents
            )
            
            # 执行请求后中间件
            if self.middleware and self.middleware.on_after_request:
                # 这里需要等待流处理完成才能获取输出消息
                # 暂时传入空列表，实际实现中可能需要更复杂的处理
                after_options = AfterRequestOptions(
                    thread_id=thread_id,
                    run_id=run_id,
                    input_messages=request.messages,
                    output_messages=[],  # TODO: 从事件源获取输出消息
                    properties=request.context.properties,
                    url=request.context.url
                )
                
                if asyncio.iscoroutinefunction(self.middleware.on_after_request):
                    await self.middleware.on_after_request(after_options)
                else:
                    self.middleware.on_after_request(after_options)
            
            logger.info(f"✅ Runtime request processed successfully - thread_id: {thread_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing runtime request: {e}")
            raise
    
    async def _get_server_side_actions(self, request: CopilotRuntimeRequest) -> List[Action]:
        """
        获取服务端动作列表
        
        Args:
            request: 运行时请求
            
        Returns:
            动作列表
        """
        if callable(self.actions):
            # 如果是函数，调用它来获取动作
            context = {
                "properties": request.context.properties,
                "url": request.context.url
            }
            return self.actions(context)
        else:
            # 如果是列表，直接返回
            return self.actions or []
    
    async def execute_action(self, action_name: str, arguments: Dict[str, Any]) -> ActionResult:
        """
        执行指定的动作
        
        Args:
            action_name: 动作名称
            arguments: 动作参数
            
        Returns:
            动作执行结果
        """
        logger.info(f"🔧 Executing action: {action_name}")
        
        start_time = datetime.now()
        
        try:
            # 查找动作
            action = None
            server_actions = await self._get_server_side_actions(
                CopilotRuntimeRequest(
                    service_adapter=None,  # 这里只是为了获取动作，不需要适配器
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
    
    async def get_available_agents(self) -> List[Agent]:
        """
        获取可用的代理列表
        
        Returns:
            代理列表
        """
        return list(self.agents.values())
    
    async def load_agent_state(
        self, 
        agent_name: str, 
        thread_id: str
    ) -> Optional[AgentState]:
        """
        加载代理状态
        
        Args:
            agent_name: 代理名称
            thread_id: 线程ID
            
        Returns:
            代理状态或None
        """
        # 这里可以实现代理状态的持久化加载逻辑
        logger.info(f"Loading agent state: {agent_name} for thread {thread_id}")
        return None
    
    async def save_agent_state(
        self, 
        agent_name: str, 
        thread_id: str, 
        state: AgentState
    ) -> None:
        """
        保存代理状态
        
        Args:
            agent_name: 代理名称
            thread_id: 线程ID
            state: 代理状态
        """
        # 这里可以实现代理状态的持久化保存逻辑
        logger.info(f"Saving agent state: {agent_name} for thread {thread_id}")
    
    def add_action(self, action: Action) -> None:
        """
        添加动作
        
        Args:
            action: 要添加的动作
        """
        if callable(self.actions):
            raise ValueError("Cannot add action when actions is a function")
        
        if isinstance(self.actions, list):
            self.actions.append(action)
        else:
            self.actions = [action]
        
        logger.info(f"Added action: {action.name}")
    
    def remove_action(self, action_name: str) -> bool:
        """
        移除动作
        
        Args:
            action_name: 动作名称
            
        Returns:
            是否成功移除
        """
        if callable(self.actions):
            raise ValueError("Cannot remove action when actions is a function")
        
        if isinstance(self.actions, list):
            for i, action in enumerate(self.actions):
                if action.name == action_name:
                    del self.actions[i]
                    logger.info(f"Removed action: {action_name}")
                    return True
        
        return False
    
    def add_agent(self, name: str, agent: Agent) -> None:
        """
        添加代理
        
        Args:
            name: 代理名称
            agent: 代理实例
        """
        self.agents[name] = agent
        logger.info(f"Added agent: {name}")
    
    def remove_agent(self, name: str) -> bool:
        """
        移除代理
        
        Args:
            name: 代理名称
            
        Returns:
            是否成功移除
        """
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent: {name}")
            return True
        return False
    
    def get_action_by_name(self, name: str) -> Optional[Action]:
        """
        根据名称获取动作
        
        Args:
            name: 动作名称
            
        Returns:
            动作实例或None
        """
        if callable(self.actions):
            # 如果是函数，需要先调用它
            actions = self.actions({})
        else:
            actions = self.actions or []
        
        for action in actions:
            if action.name == name:
                return action
        return None 