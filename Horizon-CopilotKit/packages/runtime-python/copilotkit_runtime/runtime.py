"""
CopilotKit Python 运行时核心类

本模块提供主要的 CopilotRuntime 类，处理所有 AI 请求和响应，
保持与 TypeScript 版本的兼容性。

核心功能包括：
- 处理与各种 AI 提供商的聊天完成请求
- 管理 Actions（工具调用）和代理交互
- 支持中间件和可观测性
- 管理远程端点和 MCP 服务器
- 提供完整的 GraphQL API 接口
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime

from .types import (
    Action,
    Parameter,
    Message,
    MessageInput,
    ActionInput,
    CopilotRuntimeRequest,
    CopilotRuntimeResponse,
    Middleware,
    ActionsConfiguration,
    OnBeforeRequestOptions,
    OnAfterRequestOptions,
    GraphQLContext,
    CopilotObservabilityConfig,
    Agent,
    LoadAgentStateResponse,
    ExtensionsResponse,
)
from .adapters.base import (
    CopilotServiceAdapter,
    EmptyAdapter,
    CopilotRuntimeChatCompletionRequest,
)
from .endpoints import EndpointDefinition, EndpointType, resolve_endpoint_type
from .events import RuntimeEventSource, RuntimeEventTypes
from .exceptions import CopilotKitMisuseError, CopilotKitError
from .utils import random_id, action_parameters_to_json_schema, detect_provider


class CopilotRuntime:
    """
    CopilotRuntime 主类，用于处理 AI 请求和响应。
    
    此类提供核心功能：
    - 处理各种 AI 提供商的聊天完成请求
    - 管理 Actions（工具）和工具调用
    - 处理代理交互和状态管理
    - 支持中间件和可观测性配置
    - 管理远程端点和 MCP 服务器
    - 提供与前端的完整集成接口
    
    使用示例：
        runtime = CopilotRuntime(
            actions=[weather_action, calculator_action],
            middleware=Middleware(
                on_before_request=log_request,
                on_after_request=log_response
            )
        )
    """
    
    def __init__(
        self,
        actions: Optional[ActionsConfiguration] = None,
        middleware: Optional[Middleware] = None,
        remote_endpoints: Optional[List[EndpointDefinition]] = None,
        remote_actions: Optional[List[EndpointDefinition]] = None,  # Deprecated
        langserve: Optional[List[Dict[str, Any]]] = None,
        agents: Optional[Dict[str, Any]] = None,
        delegate_agent_processing_to_service_adapter: bool = False,
        observability: Optional[CopilotObservabilityConfig] = None,
        mcp_servers: Optional[List[Dict[str, Any]]] = None,
        create_mcp_client: Optional[Callable] = None,
    ):
        """
        初始化 CopilotRuntime 实例
        
        参数:
            actions: 服务器端 Actions 配置列表，定义可用的工具和函数
            middleware: 中间件配置，用于请求/响应处理的钩子函数
            remote_endpoints: 远程端点配置，支持 LangGraph Platform 等
            remote_actions: 已弃用，请使用 remote_endpoints
            langserve: LangServe 配置（目前简化实现）
            agents: 代理配置字典，定义可用的 AI 代理
            delegate_agent_processing_to_service_adapter: 是否将代理处理委托给服务适配器
            observability: 可观测性配置，用于监控和日志记录
            mcp_servers: MCP 服务器配置列表（实验性功能）
            create_mcp_client: MCP 客户端工厂函数，用于创建 MCP 连接
        
        注意:
            - 如果同时设置 actions 和 remote_endpoints，本地 actions 可能对远程代理不可用
            - MCP 功能目前为实验性，需要提供 create_mcp_client 函数
        """
        
        # 验证 actions 与 remote endpoints 的配置
        if (actions and remote_endpoints and 
            any(resolve_endpoint_type(e) == EndpointType.LANGGRAPH_PLATFORM for e in remote_endpoints)):
            print("警告: 在运行时实例中设置的 Actions 对代理不可用")
        
        # 初始化核心属性
        self.actions = actions or []  # 服务器端 Actions 列表
        self.available_agents: List[Dict[str, str]] = []  # 可用代理列表
        
        # 处理 LangServe 配置（目前简化实现）
        self.langserve: List[Any] = []
        if langserve:
            # TODO: 实现完整的 LangServe 支持
            pass
        
        # 远程端点定义
        self.remote_endpoint_definitions = remote_endpoints or remote_actions or []
        
        # 中间件配置
        self.on_before_request = middleware.on_before_request if middleware else None
        self.on_after_request = middleware.on_after_request if middleware else None
        
        # 代理处理配置
        self.delegate_agent_processing_to_service_adapter = delegate_agent_processing_to_service_adapter
        self.observability = observability  # 可观测性配置
        self.agents = agents or {}  # 代理配置
        
        # MCP 支持（实验性功能）
        self.mcp_servers_config = mcp_servers  # MCP 服务器配置
        self.mcp_action_cache: Dict[str, List[Action]] = {}  # MCP Action 缓存
        self.create_mcp_client_impl = create_mcp_client  # MCP 客户端创建函数
        
        # 验证 MCP 配置
        if self.mcp_servers_config and not self.create_mcp_client_impl:
            raise CopilotKitMisuseError(
                "MCP 集成错误: 提供了 `mcp_servers` 配置，但没有传递 `create_mcp_client` "
                "函数给 CopilotRuntime 构造函数。请提供 `create_mcp_client` 的实现。"
            )
        
        # 对远程代理使用本地 actions 的警告
        if (actions and (
            any(resolve_endpoint_type(e) == EndpointType.LANGGRAPH_PLATFORM 
                for e in self.remote_endpoint_definitions) or 
            self.mcp_servers_config
        )):
            print(
                "警告: 在 CopilotRuntime 中定义的本地 'actions' 可能对远程代理"
                "（LangGraph、MCP）不可用。如需要，请考虑在代理实现附近定义 actions。"
            )
    
    async def process_runtime_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """
        处理运行时请求
        
        这是 CopilotRuntime 的核心方法，负责：
        - 处理代理会话和普通聊天请求
        - 执行中间件钩子函数
        - 管理事件流和响应流
        - 调用 AI 服务适配器
        - 处理工具调用和 MCP 集成
        
        参数:
            request: 要处理的运行时请求对象
            
        返回:
            CopilotRuntimeResponse: 处理后的响应对象
            
        异常:
            CopilotKitMisuseError: 当适配器配置错误时抛出
        """
        
        event_source = RuntimeEventSource()
        request_start_time = datetime.now()
        streamed_chunks: List[Any] = []
        
        try:
            # Handle agent sessions
            if request.agent_session and not self.delegate_agent_processing_to_service_adapter:
                return await self._process_agent_request(request)
            
            # Validate adapter
            if isinstance(request.service_adapter, EmptyAdapter):
                raise CopilotKitMisuseError(
                    "Invalid adapter configuration: EmptyAdapter is only meant to be used with "
                    "agent lock mode. For non-agent components like useCopilotChatSuggestions, "
                    "CopilotTextarea, or CopilotTask, please use an LLM adapter instead."
                )
            
            # Get server-side actions (including dynamic MCP)
            server_side_actions = await self._get_server_side_actions(request)
            
            # Filter messages (remove agent state messages)
            filtered_messages = [
                msg for msg in request.messages 
                if not msg.agent_state_message
            ]
            
            # Inject MCP tool instructions
            messages_with_instructions = self._inject_mcp_tool_instructions(
                filtered_messages, server_side_actions
            )
            
            # Convert messages
            converted_messages = self._convert_gql_input_to_messages(messages_with_instructions)
            
            # Call before request middleware
            if self.on_before_request:
                options = OnBeforeRequestOptions(
                    thread_id=request.thread_id,
                    run_id=request.run_id,
                    input_messages=converted_messages,
                    properties=request.graphql_context.properties,
                    url=request.url,
                )
                if asyncio.iscoroutinefunction(self.on_before_request):
                    await self.on_before_request(options)
                else:
                    self.on_before_request(options)
            
            # Prepare chat completion request
            chat_request = CopilotRuntimeChatCompletionRequest(
                event_source=event_source,
                messages=converted_messages,
                actions=self._flatten_tool_calls_no_duplicates(request.actions),
                model=None,  # Will be set by adapter
                thread_id=request.thread_id,
                run_id=request.run_id,
                forwarded_parameters=request.forwarded_parameters,
                extensions=request.extensions,
                agent_session=request.agent_session,
                agent_states=request.agent_states,
            )
            
            # Process with service adapter
            chat_response = await request.service_adapter.process(chat_request)
            
            # Wait for output messages
            output_messages = await request.output_messages_promise
            
            # Call after request middleware
            if self.on_after_request:
                options = OnAfterRequestOptions(
                    thread_id=chat_response.thread_id,
                    run_id=chat_response.run_id,
                    input_messages=converted_messages,
                    output_messages=output_messages,
                    properties=request.graphql_context.properties,
                    url=request.url,
                )
                if asyncio.iscoroutinefunction(self.on_after_request):
                    await self.on_after_request(options)
                else:
                    self.on_after_request(options)
            
            # Filter actions without agents
            action_inputs_without_agents = [
                action for action in request.actions
                # Add filtering logic here
            ]
            
            return CopilotRuntimeResponse(
                thread_id=chat_response.thread_id,
                run_id=chat_response.run_id,
                event_source=event_source,
                server_side_actions=server_side_actions,
                action_inputs_without_agents=action_inputs_without_agents,
                extensions=chat_response.extensions,
            )
            
        except Exception as e:
            # Emit error event
            event_source.emit(RuntimeEventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
            })
            raise
    
    async def discover_agents_from_endpoints(
        self, graphql_context: GraphQLContext
    ) -> List[Dict[str, Any]]:
        """Discover agents from remote endpoints"""
        agents = []
        
        for endpoint in self.remote_endpoint_definitions:
            try:
                if resolve_endpoint_type(endpoint) == EndpointType.LANGGRAPH_PLATFORM:
                    # TODO: Implement LangGraph Platform agent discovery
                    pass
                elif resolve_endpoint_type(endpoint) == EndpointType.COPILOT_KIT:
                    # TODO: Implement CopilotKit endpoint agent discovery
                    pass
            except Exception as e:
                print(f"Error discovering agents from endpoint: {e}")
        
        return agents
    
    async def load_agent_state(
        self,
        graphql_context: GraphQLContext,
        thread_id: str,
        agent_name: str,
    ) -> LoadAgentStateResponse:
        """Load agent state from remote endpoint"""
        # TODO: Implement agent state loading
        return LoadAgentStateResponse(
            state=None,
            thread_id=thread_id,
            run_id=None,
        )
    
    def _inject_mcp_tool_instructions(
        self, messages: List[MessageInput], current_actions: List[Action]
    ) -> List[MessageInput]:
        """Inject MCP tool instructions into messages"""
        # Filter for MCP tools
        mcp_actions = [action for action in current_actions if getattr(action, '_is_mcp_tool', False)]
        
        if not mcp_actions:
            return messages
        
        # Generate instructions
        instructions = self._generate_mcp_tool_instructions(mcp_actions)
        if not instructions:
            return messages
        
        # Find or create system message
        messages_copy = messages.copy()
        system_message_index = None
        
        for i, msg in enumerate(messages_copy):
            if msg.text_message and msg.text_message.role.value == "system":
                system_message_index = i
                break
        
        if system_message_index is not None:
            # Append to existing system message
            existing_msg = messages_copy[system_message_index]
            if existing_msg.text_message:
                existing_msg.text_message.content += f"\n\n{instructions}"
        else:
            # Create new system message
            from .types import MessageRole, TextMessageInput
            system_message = MessageInput(
                id=random_id(),
                created_at=datetime.now(),
                text_message=TextMessageInput(
                    role=MessageRole.SYSTEM,
                    content=instructions,
                ),
            )
            messages_copy.insert(0, system_message)
        
        return messages_copy
    
    def _generate_mcp_tool_instructions(self, mcp_actions: List[Action]) -> Optional[str]:
        """Generate instructions for MCP tools"""
        if not mcp_actions:
            return None
        
        instructions = (
            "You have access to the following tools provided by external "
            "Model Context Protocol (MCP) servers:\n"
        )
        
        for action in mcp_actions:
            instructions += f"\n- {action.name}: {action.description or 'No description'}"
        
        instructions += "\n\nUse them when appropriate to fulfill the user's request."
        return instructions
    
    async def _process_agent_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """Process agent-specific request"""
        # TODO: Implement agent request processing
        event_source = RuntimeEventSource()
        
        return CopilotRuntimeResponse(
            thread_id=request.thread_id or random_id(),
            run_id=request.run_id,
            event_source=event_source,
            server_side_actions=[],
            action_inputs_without_agents=[],
        )
    
    async def _get_server_side_actions(self, request: CopilotRuntimeRequest) -> List[Action]:
        """Get server-side actions including MCP actions"""
        actions = []
        
        # Get local actions
        if callable(self.actions):
            local_actions = self.actions({
                "properties": request.graphql_context.properties,
                "url": request.url,
            })
        else:
            local_actions = self.actions
        
        actions.extend(local_actions)
        
        # Get MCP actions (if configured)
        if self.mcp_servers_config:
            mcp_actions = await self._get_mcp_actions()
            actions.extend(mcp_actions)
        
        return actions
    
    async def _get_mcp_actions(self) -> List[Action]:
        """Get actions from MCP servers"""
        # TODO: Implement MCP action retrieval
        return []
    
    def _convert_gql_input_to_messages(self, message_inputs: List[MessageInput]) -> List[Message]:
        """Convert GraphQL message inputs to Message objects"""
        messages = []
        
        for msg_input in message_inputs:
            message = Message(
                id=msg_input.id,
                created_at=msg_input.created_at,
                text_message=msg_input.text_message,
                action_execution_message=msg_input.action_execution_message,
                result_message=msg_input.result_message,
                agent_state_message=msg_input.agent_state_message,
                image_message=msg_input.image_message,
            )
            messages.append(message)
        
        return messages
    
    def _flatten_tool_calls_no_duplicates(self, tools_by_priority: List[ActionInput]) -> List[ActionInput]:
        """Flatten tool calls and remove duplicates"""
        seen_names = set()
        result = []
        
        for tool in tools_by_priority:
            if tool.name not in seen_names:
                seen_names.add(tool.name)
                result.append(tool)
        
        return result
    
    def _detect_provider(self, service_adapter: CopilotServiceAdapter) -> Optional[str]:
        """Detect provider from service adapter"""
        return detect_provider(type(service_adapter).__name__) 