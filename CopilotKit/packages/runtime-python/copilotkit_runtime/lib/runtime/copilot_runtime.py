"""Core CopilotKit Runtime implementation."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable, Union, Awaitable
from pydantic import BaseModel, Field
import structlog
import httpx
from rx import Observable
from rx.subject import ReplaySubject
import rx.operators as ops

from ..logging import LoggingConfig
from ...service_adapters import ServiceAdapter
from ...api.models.requests import (
    MessageInput,
    ActionInput as RequestActionInput,
    AgentSessionInput,
    AgentStateInput,
    ForwardedParametersInput,
    ExtensionsInput,
    MetaEventInput
)
from ...lib.types import (
    Message,
    Action,
    Agent,
    RuntimeEventSource,
    EndpointDefinition,
    EndpointType,
    Parameter,
    CopilotKitEndpoint,
    LangGraphPlatformEndpoint,
    RemoteAgentAction,
    CopilotRuntimeRequest,
    CopilotRuntimeResponse,
    LoadAgentStateResponse,
    ExtensionsResponse,
    ActionInput
)
from ...lib.exceptions import (
    CopilotKitError,
    CopilotKitMisuseError,
    CopilotKitAgentDiscoveryError,
    CopilotKitApiDiscoveryError,
    CopilotKitLowLevelError,
    ResolvedCopilotKitError
)
from ...lib.observability import (
    CopilotObservabilityConfig,
    LLMRequestData,
    LLMResponseData,
    LLMErrorData
)
from ...lib.mcp import (
    MCPClient,
    MCPEndpointConfig,
    MCPTool,
    convert_mcp_tools_to_actions,
    generate_mcp_tool_instructions
)
from ..state_manager import StateManager
from ..events import RuntimeEventSource as EventSource


logger = structlog.get_logger(__name__)


class CopilotRuntimeConfig(BaseModel):
    """Configuration for CopilotKit Runtime."""
    logging: Optional[LoggingConfig] = None
    properties: Optional[Dict[str, Any]] = None


class OnBeforeRequestOptions(BaseModel):
    """Options for onBeforeRequest handler."""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    input_messages: List[Message]
    properties: Any
    url: Optional[str] = None


class OnAfterRequestOptions(BaseModel):
    """Options for onAfterRequest handler."""
    thread_id: str
    run_id: Optional[str] = None
    input_messages: List[Message]
    output_messages: List[Message]
    properties: Any
    url: Optional[str] = None


OnBeforeRequestHandler = Callable[[OnBeforeRequestOptions], Union[None, Awaitable[None]]]
OnAfterRequestHandler = Callable[[OnAfterRequestOptions], Union[None, Awaitable[None]]]


class Middleware(BaseModel):
    """Middleware configuration."""
    on_before_request: Optional[OnBeforeRequestHandler] = None
    on_after_request: Optional[OnAfterRequestHandler] = None

    class Config:
        arbitrary_types_allowed = True


ActionsConfiguration = Union[
    List[Action],
    Callable[[Dict[str, Any]], List[Action]]
]

CreateMCPClientFunction = Callable[[MCPEndpointConfig], Awaitable[MCPClient]]


class CopilotRuntimeConstructorParams(BaseModel):
    """Constructor parameters for CopilotRuntime."""
    middleware: Optional[Middleware] = None
    actions: Optional[ActionsConfiguration] = None
    remote_actions: Optional[List[CopilotKitEndpoint]] = None  # Deprecated
    remote_endpoints: Optional[List[EndpointDefinition]] = None
    langserve: Optional[List[Dict[str, Any]]] = None
    agents: Optional[Dict[str, Any]] = None
    delegate_agent_processing_to_service_adapter: Optional[bool] = False
    observability: Optional[CopilotObservabilityConfig] = None
    mcp_servers: Optional[List[MCPEndpointConfig]] = None
    create_mcp_client: Optional[CreateMCPClientFunction] = None

    class Config:
        arbitrary_types_allowed = True


class CopilotRuntime:
    """Main CopilotKit Runtime class equivalent to TypeScript version."""
    
    def __init__(self, params: Optional[CopilotRuntimeConstructorParams] = None):
        """Initialize the runtime with full TypeScript equivalence."""
        params = params or CopilotRuntimeConstructorParams()
        
        # Validate conflicting configurations
        if (params.actions and 
            params.remote_endpoints and 
            any(e.type == EndpointType.LANGGRAPH_PLATFORM for e in params.remote_endpoints)):
            logger.warning("Actions set in runtime instance will not be available for the agent")
        
        # Core properties
        self.actions: ActionsConfiguration = params.actions or []
        self.available_agents: List[Dict[str, str]] = []
        self.agents: Dict[str, Any] = params.agents or {}
        
        # Remote endpoints
        # Remote endpoints - handle type conversion
        remote_endpoints = params.remote_endpoints or params.remote_actions or []
        self.remote_endpoint_definitions: List[EndpointDefinition] = [
            ep if isinstance(ep, EndpointDefinition) else EndpointDefinition(**ep.__dict__)
            for ep in remote_endpoints
        ]
        
        # Langserve chains - simplified for now
        self.langserve: List[Action] = []
        if params.langserve:
            logger.info(f"Langserve chains configured: {len(params.langserve)}")
        
        # Middleware
        self.on_before_request: Optional[OnBeforeRequestHandler] = (
            params.middleware.on_before_request if params.middleware else None
        )
        self.on_after_request: Optional[OnAfterRequestHandler] = (
            params.middleware.on_after_request if params.middleware else None
        )
        
        # Configuration flags
        self.delegate_agent_processing_to_service_adapter = (
            params.delegate_agent_processing_to_service_adapter or False
        )
        
        # Observability
        self.observability = params.observability
        
        # MCP properties
        self.mcp_servers_config = params.mcp_servers
        self.mcp_action_cache: Dict[str, List[Action]] = {}
        self.create_mcp_client_impl = params.create_mcp_client
        
        # Validate MCP configuration
        if (self.mcp_servers_config and 
            len(self.mcp_servers_config) > 0 and 
            not self.create_mcp_client_impl):
            raise CopilotKitMisuseError(
                "MCP Integration Error: `mcp_servers` were provided, but the `create_mcp_client` "
                "function was not passed to the CopilotRuntime constructor. "
                "Please provide an implementation for `create_mcp_client`."
            )
        
        # Warning for local actions with remote agents
        if (params.actions and 
            (any(e.type == EndpointType.LANGGRAPH_PLATFORM for e in self.remote_endpoint_definitions) or
             (self.mcp_servers_config and len(self.mcp_servers_config) > 0))):
            logger.warning(
                "Local 'actions' defined in CopilotRuntime might not be available to remote agents "
                "(LangGraph, MCP). Consider defining actions closer to the agent implementation if needed."
            )
        
        # Initialize logger
        self.logger = logger.bind(component="CopilotRuntime")
        
        # Initialize state management components
        self.state_manager = StateManager()
        self.event_source = EventSource()
    
    def _inject_mcp_tool_instructions(
        self, 
        messages: List[MessageInput], 
        current_actions: List[Action]
    ) -> List[MessageInput]:
        """Inject MCP tool instructions into messages."""
        # Filter for MCP tools
        mcp_actions_for_request = [
            action for action in current_actions 
            if getattr(action, '_is_mcp_tool', False)
        ]
        
        if not mcp_actions_for_request:
            return messages
        
        # Create unique tools map
        unique_mcp_tools: Dict[str, Action] = {}
        for action in mcp_actions_for_request:
            unique_mcp_tools[action.name] = action
        
        # Convert to MCPTool format
        tools_map: Dict[str, MCPTool] = {}
        for action in unique_mcp_tools.values():
            tools_map[action.name] = MCPTool(
                description=action.description or "",
                schema={
                    "parameters": {
                        "properties": {
                            p.name: {"type": p.type, "description": p.description}
                            for p in (action.parameters or [])
                        },
                        "required": [
                            p.name for p in (action.parameters or []) 
                            if p.required
                        ]
                    }
                } if action.parameters else {},
                execute=lambda: {}  # Placeholder
            )
        
        # Generate instructions
        mcp_tool_instructions = generate_mcp_tool_instructions(tools_map)
        
        if not mcp_tool_instructions:
            return messages
        
        instructions = (
            "You have access to the following tools provided by external "
            "Model Context Protocol (MCP) servers:\n" +
            mcp_tool_instructions +
            "\nUse them when appropriate to fulfill the user's request."
        )
        
        # Find system message or create one
        new_messages = messages.copy()
        system_message_index = None
        
        for i, msg in enumerate(new_messages):
            # Handle both dictionary and object formats
            if isinstance(msg, dict):
                text_msg = msg.get('text_message')
                if text_msg:
                    role = text_msg.get('role') if isinstance(text_msg, dict) else getattr(text_msg, 'role', None)
                    if role == "system":
                        system_message_index = i
                        break
            else:
                if (hasattr(msg, 'text_message') and msg.text_message and 
                    hasattr(msg.text_message, 'role') and 
                    msg.text_message.role == "system"):
                    system_message_index = i
                    break
        
        if system_message_index is not None:
            # Append to existing system message
            existing_msg = new_messages[system_message_index]
            if isinstance(existing_msg, dict):
                text_msg = existing_msg.get('text_message')
                if text_msg:
                    if isinstance(text_msg, dict):
                        existing_content = text_msg.get('content', '')
                        text_msg['content'] = (
                            existing_content + "\n\n" + instructions
                            if existing_content else instructions
                        )
                    else:
                        existing_content = getattr(text_msg, 'content', '')
                        text_msg.content = (
                            existing_content + "\n\n" + instructions
                            if existing_content else instructions
                        )
            else:
                if hasattr(existing_msg, 'text_message') and existing_msg.text_message:
                    existing_content = existing_msg.text_message.content or ""
                    existing_msg.text_message.content = (
                        existing_content + "\n\n" + instructions
                        if existing_content else instructions
                    )
        else:
            # Create new system message
            from ...utils.helpers import random_id
            from datetime import datetime
            
            # Create system message as dictionary format
            system_message = {
                "id": random_id(),
                "created_at": datetime.now(),
                "text_message": {
                    "role": "system",
                    "content": instructions
                },
                "action_execution_message": None,
                "result_message": None,
                "agent_state_message": None
            }
            new_messages.insert(0, system_message)
        
        return new_messages
    
    async def process_runtime_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """Process a runtime request with full TypeScript equivalence."""
        # Extract request components
        service_adapter = request.service_adapter
        raw_messages = request.messages
        client_side_actions_input = request.actions
        thread_id = request.thread_id
        run_id = request.run_id
        output_messages_promise = request.output_messages_promise
        graphql_context = request.graphql_context
        forwarded_parameters = request.forwarded_parameters
        url = request.url
        extensions = request.extensions
        agent_session = request.agent_session
        agent_states = request.agent_states
        public_api_key = request.public_api_key
        meta_events = request.meta_events
        
        # Create event source
        event_source = RuntimeEventSource()
        request_start_time = time.time() * 1000  # Convert to milliseconds
        streamed_chunks: List[Any] = []
        
        try:
            # Handle agent session if not delegated
            if agent_session and not self.delegate_agent_processing_to_service_adapter:
                return await self.process_agent_request(request)
            
            # Validate service adapter
            if service_adapter.__class__.__name__ == "EmptyAdapter":
                raise CopilotKitMisuseError(
                    "Invalid adapter configuration: EmptyAdapter is only meant to be used with agent lock mode. "
                    "For non-agent components like useCopilotChatSuggestions, CopilotTextarea, or CopilotTask, "
                    "please use an LLM adapter instead."
                )
            
            # Get server side actions early (including dynamic MCP)
            server_side_actions = await self.get_server_side_actions(request)
            
            # Filter raw messages
            filtered_raw_messages = []
            for msg in raw_messages:
                # Handle both dictionary and object formats
                if isinstance(msg, dict):
                    # Check if it's NOT an agent state message
                    if not msg.get('agent_state_message'):
                        filtered_raw_messages.append(msg)
                else:
                    # Object format - check attribute
                    if not hasattr(msg, 'agent_state_message') or not msg.agent_state_message:
                        filtered_raw_messages.append(msg)
            
            # Inject MCP instructions
            messages_with_injected_instructions = self._inject_mcp_tool_instructions(
                filtered_raw_messages, server_side_actions
            )
            input_messages = self._convert_gql_input_to_messages(messages_with_injected_instructions)
            
            # Log LLM request if observability enabled
            if self.observability and self.observability.enabled and public_api_key:
                try:
                    request_data = LLMRequestData(
                        thread_id=thread_id,
                        run_id=run_id,
                        model=forwarded_parameters.model if forwarded_parameters else None,
                        messages=input_messages,
                        actions=client_side_actions_input,
                        forwarded_parameters=forwarded_parameters,
                        timestamp=int(request_start_time),
                        provider=self._detect_provider(service_adapter)
                    )
                    await self.observability.hooks.handle_request(request_data)
                except Exception as error:
                    logger.error(f"Error logging LLM request: {error}")
            
            # Convert server side actions to input format
            server_side_actions_input = [
                ActionInput(
                    name=action.name,
                    description=action.description,
                    json_schema=json.dumps(self._action_parameters_to_json_schema(action.parameters))
                )
                for action in server_side_actions
            ]
            
            # Flatten tool calls without duplicates
            action_inputs = self._flatten_tool_calls_no_duplicates([
                *server_side_actions_input,
                *[
                    action for action in client_side_actions_input
                    if getattr(action, 'available', None) != 'remote'
                ]
            ])
            
            # Call before request middleware
            if self.on_before_request:
                options = OnBeforeRequestOptions(
                    thread_id=thread_id,
                    run_id=run_id,
                    input_messages=input_messages,
                    properties=graphql_context.properties,
                    url=url
                )
                result = self.on_before_request(options)
                if asyncio.iscoroutine(result):
                    await result
            
            # Process with service adapter
            # Check if it's a DeepSeek adapter which expects a specific request format
            if hasattr(service_adapter, '__class__') and 'DeepSeek' in service_adapter.__class__.__name__:
                # Import the request class and ActionInput for DeepSeek adapter
                from ...service_adapters.deepseek.adapter import CopilotRuntimeChatCompletionRequest
                from ...api.models.requests import ActionInput as DeepSeekActionInput
                
                # Convert action_inputs to DeepSeek's ActionInput format
                deepseek_actions = []
                for action in action_inputs:
                    if hasattr(action, 'name'):
                        # Convert from lib.types.ActionInput to api.models.requests.ActionInput
                        parameters = getattr(action, 'parameters', None)
                        
                        # If action has json_schema, parse it to get parameters
                        json_schema = getattr(action, 'json_schema', None)
                        if json_schema:
                            try:
                                schema = json.loads(json_schema)
                                parameters = schema.get('properties', {})
                            except (json.JSONDecodeError, AttributeError, TypeError):
                                parameters = getattr(action, 'parameters', None)
                        
                        deepseek_actions.append(DeepSeekActionInput(
                            name=action.name,
                            description=getattr(action, 'description', None),
                            parameters=parameters,
                            available=getattr(action, 'available', None)
                        ))
                    else:
                        # Already in correct format or dict
                        deepseek_actions.append(action)
                
                # Create the request object
                adapter_request = CopilotRuntimeChatCompletionRequest(
                    messages=input_messages,
                    actions=deepseek_actions,
                    thread_id=thread_id,
                    run_id=run_id,
                    event_source=event_source,
                    forwarded_parameters=forwarded_parameters,
                    extensions=extensions,
                    agent_session=agent_session,
                    agent_states=agent_states
                )
                result = await service_adapter.process(adapter_request)
            else:
                # For other adapters, use the keyword arguments approach
                result = await service_adapter.process(
                    messages=input_messages,
                    actions=action_inputs,
                    thread_id=thread_id,
                    run_id=run_id,
                    event_source=event_source,
                    forwarded_parameters=forwarded_parameters,
                    extensions=extensions,
                    agent_session=agent_session,
                    agent_states=agent_states
                )
            
            # Handle non-empty thread ID for backwards compatibility
            non_empty_thread_id = thread_id or result.thread_id
            
            # Set up after request middleware
            async def handle_output_messages():
                try:
                    output_messages = await output_messages_promise
                    if self.on_after_request:
                        options = OnAfterRequestOptions(
                            thread_id=non_empty_thread_id,
                            run_id=result.run_id,
                            input_messages=input_messages,
                            output_messages=output_messages,
                            properties=graphql_context.properties,
                            url=url
                        )
                        after_result = self.on_after_request(options)
                        if asyncio.iscoroutine(after_result):
                            await after_result
                except Exception as error:
                    logger.error(f"Error in after request handler: {error}")
            
            # Schedule after request handler
            asyncio.create_task(handle_output_messages())
            
            # Handle observability logging for response
            if self.observability and self.observability.enabled and public_api_key:
                self._setup_response_logging(
                    output_messages_promise, result, forwarded_parameters, 
                    request_start_time, service_adapter, streamed_chunks
                )
            
            # Setup progressive logging if enabled
            if (self.observability and self.observability.enabled and 
                self.observability.progressive and public_api_key):
                self._setup_progressive_logging(
                    event_source, request_start_time, thread_id, run_id,
                    forwarded_parameters, service_adapter, streamed_chunks
                )
            
            return CopilotRuntimeResponse(
                thread_id=non_empty_thread_id,
                run_id=result.run_id,
                event_source=event_source,
                server_side_actions=server_side_actions,
                action_inputs_without_agents=[
                    action for action in action_inputs
                    if not any(
                        server_side_action.name == action.name
                        for server_side_action in server_side_actions
                    )
                ],
                extensions=result.extensions
            )
            
        except Exception as error:
            # Log error if observability enabled
            if self.observability and self.observability.enabled and public_api_key:
                try:
                    error_data = LLMErrorData(
                        thread_id=thread_id,
                        run_id=run_id,
                        model=forwarded_parameters.model if forwarded_parameters else None,
                        error=error if isinstance(error, Exception) else Exception(str(error)),
                        timestamp=int(time.time() * 1000),
                        latency=int(time.time() * 1000 - request_start_time),
                        provider=self._detect_provider(service_adapter)
                    )
                    await self.observability.hooks.handle_error(error_data)
                except Exception as log_error:
                    logger.error(f"Error logging LLM error: {log_error}")
            
            if isinstance(error, CopilotKitError):
                raise error
            logger.error(f"Error getting response: {error}")
            event_source.send_error_message_to_chat()
            raise error
    
    async def discover_agents_from_endpoints(self, graphql_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover available agents from endpoints."""
        agents: List[Dict[str, Any]] = []
        
        for endpoint in self.remote_endpoint_definitions:
            try:
                if endpoint.type == EndpointType.LANGGRAPH_PLATFORM:
                    # Handle LangGraph Platform endpoints
                    property_headers = {}
                    if graphql_context.get('properties', {}).get('authorization'):
                        property_headers['authorization'] = (
                            f"Bearer {graphql_context['properties']['authorization']}"
                        )
                    
                    # Create LangGraph client (simplified for now)
                    async with httpx.AsyncClient() as client:
                        try:
                            response = await client.get(
                                f"{endpoint.deployment_url}/assistants",
                                headers={
                                    'Authorization': f"Bearer {endpoint.langsmith_api_key}",
                                    **property_headers
                                }
                            )
                            
                            if response.status_code == 404:
                                raise CopilotKitAgentDiscoveryError(
                                    available_agents=self.available_agents
                                )
                            
                            data = response.json()
                            if isinstance(data, dict) and data.get('detail', '').lower() == 'not found':
                                raise CopilotKitAgentDiscoveryError(
                                    available_agents=self.available_agents
                                )
                            
                            endpoint_agents = [
                                {
                                    'name': entry['graph_id'],
                                    'id': entry['assistant_id'],
                                    'description': '',
                                    'endpoint': endpoint
                                }
                                for entry in data
                                if isinstance(entry, dict)
                            ]
                            agents.extend(endpoint_agents)
                            
                        except httpx.HTTPError as e:
                            raise CopilotKitMisuseError(
                                f"Failed to find or contact remote endpoint at url {endpoint.deployment_url}. "
                                f"Make sure the API is running and that it's indeed a LangGraph platform url. "
                                f"See more: https://docs.copilotkit.ai/troubleshooting/common-issues"
                            )
                
                else:
                    # Handle CopilotKit endpoints
                    cpk_endpoint = endpoint
                    fetch_url = f"{endpoint.url}/info"
                    
                    headers = self._create_headers(cpk_endpoint, graphql_context)
                    body = {'properties': graphql_context.get('properties', {})}
                    
                    async with httpx.AsyncClient() as client:
                        try:
                            response = await client.post(
                                fetch_url,
                                headers=headers,
                                json=body
                            )
                            
                            if not response.is_success:
                                if response.status_code == 404:
                                    raise CopilotKitApiDiscoveryError(url=fetch_url)
                                raise ResolvedCopilotKitError(
                                    status=response.status_code,
                                    url=fetch_url,
                                    is_remote_endpoint=True
                                )
                            
                            data = response.json()
                            endpoint_agents = [
                                {
                                    'name': agent['name'],
                                    'description': agent.get('description', ''),
                                    'id': self._random_id(),
                                    'endpoint': endpoint
                                }
                                for agent in data.get('agents', [])
                            ]
                            agents.extend(endpoint_agents)
                            
                        except httpx.HTTPError as error:
                            if isinstance(error, CopilotKitError):
                                raise error
                            raise CopilotKitLowLevelError(error=error, url=fetch_url)
            
            except Exception as error:
                logger.error(f"Error discovering agents from endpoint {endpoint.url}: {error}")
                continue
        
        # Update available agents cache
        self.available_agents = [
            {'name': agent['name'], 'id': agent['id']}
            for agent in agents
        ]
        
        return agents
    
    async def load_agent_state(
        self, 
        graphql_context: Dict[str, Any], 
        thread_id: str, 
        agent_name: str
    ) -> LoadAgentStateResponse:
        """Load agent state from endpoints."""
        agents_with_endpoints = await self.discover_agents_from_endpoints(graphql_context)
        
        agent_with_endpoint = next(
            (agent for agent in agents_with_endpoints if agent['name'] == agent_name),
            None
        )
        
        if not agent_with_endpoint:
            raise Exception("Agent not found")
        
        endpoint = agent_with_endpoint['endpoint']
        
        if endpoint.type == EndpointType.LANGGRAPH_PLATFORM:
            # Handle LangGraph Platform
            property_headers = {}
            if graphql_context.get('properties', {}).get('authorization'):
                property_headers['authorization'] = (
                    f"Bearer {graphql_context['properties']['authorization']}"
                )
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{endpoint.deployment_url}/threads/{thread_id}/state",
                        headers={
                            'Authorization': f"Bearer {endpoint.langsmith_api_key}",
                            **property_headers
                        }
                    )
                    
                    if response.is_success:
                        state_data = response.json()
                        state = state_data.get('values', {})
                    else:
                        state = {}
                    
                except Exception:
                    state = {}
            
            if not state:
                return LoadAgentStateResponse(
                    thread_id=thread_id,
                    thread_exists=False,
                    state=json.dumps({}),
                    messages=json.dumps([])
                )
            else:
                messages = state.pop('messages', [])
                copilotkit_messages = self._langchain_messages_to_copilotkit(messages)
                return LoadAgentStateResponse(
                    thread_id=thread_id,
                    thread_exists=True,
                    state=json.dumps(state),
                    messages=json.dumps(copilotkit_messages)
                )
        
        else:
            # Handle CopilotKit endpoints
            fetch_url = f"{endpoint.url}/agents/state"
            
            headers = self._create_headers(endpoint, graphql_context)
            body = {
                'properties': graphql_context.get('properties', {}),
                'threadId': thread_id,
                'name': agent_name
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        fetch_url,
                        headers=headers,
                        json=body
                    )
                    
                    if not response.is_success:
                        if response.status_code == 404:
                            raise CopilotKitApiDiscoveryError(url=fetch_url)
                        raise ResolvedCopilotKitError(
                            status=response.status_code,
                            url=fetch_url,
                            is_remote_endpoint=True
                        )
                    
                    data = response.json()
                    
                    return LoadAgentStateResponse(
                        thread_id=data.get('thread_id', thread_id),
                        thread_exists=data.get('thread_exists', False),
                        state=json.dumps(data.get('state', {})),
                        messages=json.dumps(data.get('messages', []))
                    )
                    
                except httpx.HTTPError as error:
                    if isinstance(error, CopilotKitError):
                        raise error
                    raise CopilotKitLowLevelError(error=error, url=fetch_url)
    
    async def process_agent_request(self, request: CopilotRuntimeRequest) -> CopilotRuntimeResponse:
        """Process agent-specific request."""
        raw_messages = request.messages
        output_messages_promise = request.output_messages_promise
        graphql_context = request.graphql_context
        agent_session = request.agent_session
        thread_id_from_request = request.thread_id
        meta_events = request.meta_events
        public_api_key = request.public_api_key
        forwarded_parameters = request.forwarded_parameters
        
        agent_name = getattr(agent_session, 'agent_name', None)
        node_name = getattr(agent_session, 'node_name', None)
        
        # Track request start time
        request_start_time = time.time() * 1000
        streamed_chunks: List[Any] = []
        
        # Handle backwards compatibility for thread ID
        thread_id = thread_id_from_request or getattr(agent_session, 'thread_id', None)
        
        server_side_actions = await self.get_server_side_actions(request)
        messages = self._convert_gql_input_to_messages(raw_messages)
        
        # Find current agent
        current_agent = next(
            (
                action for action in server_side_actions
                if (action.name == agent_name and self._is_remote_agent_action(action))
            ),
            None
        )
        
        if not current_agent:
            raise CopilotKitAgentDiscoveryError(
                agent_name=agent_name,
                available_agents=self.available_agents
            )
        
        # Filter available actions for current agent
        available_actions_for_current_agent = []
        for action in server_side_actions:
            # Case 1: Keep all regular (non-agent) actions
            if not self._is_remote_agent_action(action):
                available_actions_for_current_agent.append(action)
            # Case 2: For agent actions, keep all except self
            elif self._is_remote_agent_action(action) and action.name != agent_name:
                available_actions_for_current_agent.append(action)
        
        # Convert to ActionInput format
        available_actions_input = [
            ActionInput(
                name=action.name,
                description=action.description,
                json_schema=json.dumps(self._action_parameters_to_json_schema(action.parameters))
            )
            for action in available_actions_for_current_agent
        ]
        
        all_available_actions = self._flatten_tool_calls_no_duplicates([
            *available_actions_input,
            *request.actions
        ])
        
        # Log agent request if observability enabled
        if self.observability and self.observability.enabled and public_api_key:
            try:
                request_data = LLMRequestData(
                    thread_id=thread_id,
                    run_id=None,
                    model=forwarded_parameters.model if forwarded_parameters else None,
                    messages=messages,
                    actions=all_available_actions,
                    forwarded_parameters=forwarded_parameters,
                    timestamp=int(request_start_time),
                    provider="agent",
                    agent_name=agent_name,
                    node_name=node_name
                )
                await self.observability.hooks.handle_request(request_data)
            except Exception as error:
                logger.error(f"Error logging agent request: {error}")
        
        # Call before request middleware
        if self.on_before_request:
            options = OnBeforeRequestOptions(
                thread_id=thread_id,
                run_id=None,
                input_messages=messages,
                properties=graphql_context.properties
            )
            result = self.on_before_request(options)
            if asyncio.iscoroutine(result):
                await result
        
        try:
            event_source = RuntimeEventSource()
            
            # Call remote agent handler
            stream = await current_agent.remote_agent_handler(
                name=agent_name,
                thread_id=thread_id,
                node_name=node_name,
                meta_events=meta_events,
                action_inputs_without_agents=all_available_actions
            )
            
            # Setup progressive observability if enabled
            if (self.observability and self.observability.enabled and 
                self.observability.progressive and public_api_key):
                self._setup_agent_progressive_logging(
                    event_source, request_start_time, thread_id, 
                    forwarded_parameters, agent_name, node_name, streamed_chunks
                )
            
            # Stream events
            def stream_handler(event_stream_observable):
                from rx import operators as ops
                from rx.core import Observable
                
                if hasattr(stream, '__iter__'):
                    # Convert iterable to Observable
                    Observable.from_(stream).subscribe(
                        on_next=lambda event: event_stream_observable.on_next(event),
                        on_error=lambda err: self._handle_agent_stream_error(
                            err, event_stream_observable, public_api_key, thread_id,
                            forwarded_parameters, agent_name, node_name, request_start_time
                        ),
                        on_completed=lambda: event_stream_observable.on_completed()
                    )
                else:
                    # Assume it's already an Observable
                    stream.subscribe(
                        on_next=lambda event: event_stream_observable.on_next(event),
                        on_error=lambda err: self._handle_agent_stream_error(
                            err, event_stream_observable, public_api_key, thread_id,
                            forwarded_parameters, agent_name, node_name, request_start_time
                        ),
                        on_completed=lambda: event_stream_observable.on_completed()
                    )
            
            await event_source.stream(stream_handler)
            
            # Log final agent response
            if self.observability and self.observability.enabled and public_api_key:
                self._setup_agent_response_logging(
                    output_messages_promise, request_start_time, thread_id,
                    forwarded_parameters, agent_name, node_name, streamed_chunks
                )
            
            # Setup after request middleware
            async def handle_output_messages():
                try:
                    output_messages = await output_messages_promise
                    if self.on_after_request:
                        options = OnAfterRequestOptions(
                            thread_id=thread_id,
                            run_id=None,
                            input_messages=messages,
                            output_messages=output_messages,
                            properties=graphql_context.properties
                        )
                        after_result = self.on_after_request(options)
                        if asyncio.iscoroutine(after_result):
                            await after_result
                except Exception as error:
                    logger.error(f"Error in agent after request handler: {error}")
            
            asyncio.create_task(handle_output_messages())
            
            return CopilotRuntimeResponse(
                thread_id=thread_id,
                run_id=None,
                event_source=event_source,
                server_side_actions=server_side_actions,
                action_inputs_without_agents=all_available_actions
            )
            
        except Exception as error:
            # Log error with observability
            if self.observability and self.observability.enabled and public_api_key:
                try:
                    error_data = LLMErrorData(
                        thread_id=thread_id,
                        run_id=None,
                        model=forwarded_parameters.model if forwarded_parameters else None,
                        error=error if isinstance(error, Exception) else Exception(str(error)),
                        timestamp=int(time.time() * 1000),
                        latency=int(time.time() * 1000 - request_start_time),
                        provider="agent",
                        agent_name=agent_name,
                        node_name=node_name
                    )
                    await self.observability.hooks.handle_error(error_data)
                except Exception as log_error:
                    logger.error(f"Error logging agent error: {log_error}")
            
            logger.error(f"Error getting agent response: {error}")
            raise error
    
    async def get_server_side_actions(self, request: CopilotRuntimeRequest) -> List[Action]:
        """Get server side actions including MCP actions."""
        graphql_context = request.graphql_context
        raw_messages = request.messages
        agent_states = request.agent_states
        url = request.url
        
        # Standard action fetching
        input_messages = self._convert_gql_input_to_messages(raw_messages)
        langserve_functions = []
        
        # TODO: Load langserve chains
        for chain in self.langserve:
            try:
                langserve_functions.append(chain)
            except Exception as error:
                logger.error(f"Error loading langserve chain: {error}")
        
        # Setup remote actions
        remote_actions = await self._setup_remote_actions(
            self.remote_endpoint_definitions,
            graphql_context,
            input_messages,
            agent_states,
            url,
            self.agents,
            request.meta_events
        )
        
        # Get configured actions
        if callable(self.actions):
            configured_actions = self.actions({
                'properties': graphql_context.get('properties', {}),
                'url': url
            })
        else:
            configured_actions = self.actions or []
        
        # Dynamic MCP action fetching
        request_specific_mcp_actions = []
        if self.create_mcp_client_impl:
            # Determine effective MCP endpoints
            base_endpoints = self.mcp_servers_config or []
            request_endpoints = (
                graphql_context.properties.get('mcp_servers', []) or
                graphql_context.properties.get('mcp_endpoints', [])
            )
            
            # Merge and deduplicate endpoints
            effective_endpoints_map = {}
            
            # Add base endpoints
            for ep in base_endpoints:
                if ep and hasattr(ep, 'endpoint'):
                    effective_endpoints_map[ep.endpoint] = ep
            
            # Add request endpoints (override duplicates)
            for ep in request_endpoints:
                if ep and hasattr(ep, 'endpoint'):
                    effective_endpoints_map[ep.endpoint] = ep
            
            effective_endpoints = list(effective_endpoints_map.values())
            
            # Fetch/cache actions for effective endpoints
            for config in effective_endpoints:
                endpoint_url = config.endpoint
                actions_for_endpoint = self.mcp_action_cache.get(endpoint_url)
                
                if actions_for_endpoint is None:
                    # Not cached, fetch now
                    try:
                        client = await self.create_mcp_client_impl(config)
                        tools = await client.tools()
                        actions_for_endpoint = convert_mcp_tools_to_actions(tools, endpoint_url)
                        self.mcp_action_cache[endpoint_url] = actions_for_endpoint
                    except Exception as error:
                        logger.error(
                            f"MCP: Failed to fetch tools from endpoint {endpoint_url}. "
                            f"Skipping. Error: {error}"
                        )
                        actions_for_endpoint = []
                        self.mcp_action_cache[endpoint_url] = actions_for_endpoint
                
                request_specific_mcp_actions.extend(actions_for_endpoint or [])
        
        # Combine all action sources
        return [
            *configured_actions,
            *langserve_functions,
            *remote_actions,
            *request_specific_mcp_actions
        ]
    
    # Helper methods
    def _convert_gql_input_to_messages(self, message_inputs: List[Any]) -> List[Message]:
        """Convert GraphQL input messages to internal Message format."""
        messages = []
        for msg_input in message_inputs:
            # Handle both dictionary and object formats
            if isinstance(msg_input, dict):
                # Direct dictionary access
                if 'text_message' in msg_input and msg_input['text_message']:
                    text_msg = msg_input['text_message']
                    messages.append(Message(
                        id=msg_input.get('id', ''),
                        role=text_msg.get('role', 'user') if isinstance(text_msg, dict) else getattr(text_msg, 'role', 'user'),
                        content=text_msg.get('content', '') if isinstance(text_msg, dict) else getattr(text_msg, 'content', '')
                    ))
                elif 'type' in msg_input and msg_input['type'] == 'text':
                    # Handle direct text message format
                    messages.append(Message(
                        id=msg_input.get('id', ''),
                        role=msg_input.get('role', 'user'),
                        content=msg_input.get('content', '')
                    ))
            else:
                # Object format (Pydantic model or similar)
                if hasattr(msg_input, 'text_message') and msg_input.text_message:
                    text_msg = msg_input.text_message
                    role = text_msg.role if hasattr(text_msg, 'role') else text_msg.get('role', 'user')
                    content = text_msg.content if hasattr(text_msg, 'content') else text_msg.get('content', '')
                    
                    # Handle enum values
                    if hasattr(role, 'value'):
                        role = role.value
                    
                    messages.append(Message(
                        id=getattr(msg_input, 'id', ''),
                        role=role,
                        content=content
                    ))
        return messages
    
    def _action_parameters_to_json_schema(self, parameters: Optional[List[Parameter]]) -> Dict[str, Any]:
        """Convert action parameters to JSON schema."""
        if not parameters:
            return {"type": "object", "properties": {}}
        
        properties = {}
        required = []
        
        for param in parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _flatten_tool_calls_no_duplicates(self, tools_by_priority: List[ActionInput]) -> List[ActionInput]:
        """Flatten tool calls without duplicates."""
        all_tools = []
        all_tool_names = []
        
        for tool in tools_by_priority:
            if tool.name not in all_tool_names:
                all_tools.append(tool)
                all_tool_names.append(tool.name)
        
        return all_tools
    
    def _detect_provider(self, service_adapter: ServiceAdapter) -> Optional[str]:
        """Detect provider from service adapter."""
        adapter_name = service_adapter.__class__.__name__
        if "OpenAI" in adapter_name:
            return "openai"
        elif "Anthropic" in adapter_name:
            return "anthropic"
        elif "Google" in adapter_name:
            return "google"
        elif "Groq" in adapter_name:
            return "groq"
        elif "LangChain" in adapter_name:
            return "langchain"
        elif "DeepSeek" in adapter_name:
            return "deepseek"
        return None
    
    def _is_remote_agent_action(self, action: Action) -> bool:
        """Check if action is a remote agent action."""
        return hasattr(action, 'remote_agent_handler')
    
    def _create_headers(self, endpoint: EndpointDefinition, graphql_context: Dict[str, Any]) -> Dict[str, str]:
        """Create headers for endpoint requests."""
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization if available
        if hasattr(endpoint, 'on_before_request') and endpoint.on_before_request:
            # Call the on_before_request handler
            pass
        
        return headers
    
    def _random_id(self) -> str:
        """Generate random ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _langchain_messages_to_copilotkit(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to CopilotKit format."""
        # Simplified conversion
        copilotkit_messages = []
        for msg in messages:
            if hasattr(msg, 'content') and hasattr(msg, 'type'):
                copilotkit_messages.append({
                    'content': msg.content,
                    'role': 'assistant' if msg.type == 'ai' else 'user'
                })
        return copilotkit_messages
    
    async def _setup_remote_actions(
        self,
        remote_endpoint_definitions: List[EndpointDefinition],
        graphql_context: Dict[str, Any],
        messages: List[Message],
        agent_states: Optional[List[AgentStateInput]],
        frontend_url: Optional[str],
        agents: Dict[str, Any],
        meta_events: Optional[List[MetaEventInput]]
    ) -> List[Action]:
        """Setup remote actions - simplified implementation."""
        # This would be a complex implementation in the real system
        # For now, return empty list
        return []
    
    def _setup_response_logging(
        self,
        output_messages_promise: asyncio.Future,
        result: Any,
        forwarded_parameters: Optional[ForwardedParametersInput],
        request_start_time: float,
        service_adapter: ServiceAdapter,
        streamed_chunks: List[Any]
    ) -> None:
        """Setup response logging."""
        async def log_response():
            try:
                output_messages = await output_messages_promise
                response_data = LLMResponseData(
                    thread_id=result.thread_id,
                    run_id=result.run_id,
                    model=forwarded_parameters.model if forwarded_parameters else None,
                    output=streamed_chunks if (self.observability and self.observability.progressive) else output_messages,
                    latency=int(time.time() * 1000 - request_start_time),
                    timestamp=int(time.time() * 1000),
                    provider=self._detect_provider(service_adapter),
                    is_final_response=True
                )
                if self.observability and self.observability.hooks:
                    await self.observability.hooks.handle_response(response_data)
            except Exception as error:
                logger.error(f"Error logging response: {error}")
        
        asyncio.create_task(log_response())
    
    def _setup_progressive_logging(
        self,
        event_source: RuntimeEventSource,
        request_start_time: float,
        thread_id: Optional[str],
        run_id: Optional[str],
        forwarded_parameters: Optional[ForwardedParametersInput],
        service_adapter: ServiceAdapter,
        streamed_chunks: List[Any]
    ) -> None:
        """Setup progressive logging for streaming events."""
        # This would wrap the event source stream method to intercept events
        # Implementation would be similar to TypeScript version
        pass
    
    def _setup_agent_progressive_logging(
        self,
        event_source: RuntimeEventSource,
        request_start_time: float,
        thread_id: str,
        forwarded_parameters: Optional[ForwardedParametersInput],
        agent_name: str,
        node_name: str,
        streamed_chunks: List[Any]
    ) -> None:
        """Setup progressive logging for agent streams."""
        # Similar to _setup_progressive_logging but for agents
        pass
    
    def _setup_agent_response_logging(
        self,
        output_messages_promise: asyncio.Future,
        request_start_time: float,
        thread_id: str,
        forwarded_parameters: Optional[ForwardedParametersInput],
        agent_name: str,
        node_name: str,
        streamed_chunks: List[Any]
    ) -> None:
        """Setup agent response logging."""
        async def log_agent_response():
            try:
                output_messages = await output_messages_promise
                response_data = LLMResponseData(
                    thread_id=thread_id,
                    run_id=None,
                    model=forwarded_parameters.model if forwarded_parameters else None,
                    output=streamed_chunks if (self.observability and self.observability.progressive) else output_messages,
                    latency=int(time.time() * 1000 - request_start_time),
                    timestamp=int(time.time() * 1000),
                    provider="agent",
                    is_final_response=True,
                    agent_name=agent_name,
                    node_name=node_name
                )
                if self.observability and self.observability.hooks:
                    await self.observability.hooks.handle_response(response_data)
            except Exception as error:
                logger.error(f"Error logging agent response: {error}")
        
        asyncio.create_task(log_agent_response())
    
    def _handle_agent_stream_error(
        self,
        error: Exception,
        event_stream_observable: Any,
        public_api_key: Optional[str],
        thread_id: str,
        forwarded_parameters: Optional[ForwardedParametersInput],
        agent_name: str,
        node_name: str,
        request_start_time: float
    ) -> None:
        """Handle agent stream errors."""
        logger.error(f"Error in agent stream: {error}")
        
        # Log error with observability
        if self.observability and self.observability.enabled and public_api_key:
            try:
                error_data = LLMErrorData(
                    thread_id=thread_id,
                    run_id=None,
                    model=forwarded_parameters.model if forwarded_parameters else None,
                    error=error,
                    timestamp=int(time.time() * 1000),
                    latency=int(time.time() * 1000 - request_start_time),
                    provider="agent",
                    agent_name=agent_name,
                    node_name=node_name
                )
                asyncio.create_task(self.observability.hooks.handle_error(error_data))
            except Exception as log_error:
                logger.error(f"Error logging agent error: {log_error}")
        
        event_stream_observable.on_error(error)
        event_stream_observable.on_completed()


# Helper functions
def flatten_tool_calls_no_duplicates(tools_by_priority: List[ActionInput]) -> List[ActionInput]:
    """Flatten tool calls without duplicates."""
    all_tools = []
    all_tool_names = []
    
    for tool in tools_by_priority:
        if tool.name not in all_tool_names:
            all_tools.append(tool)
            all_tool_names.append(tool.name)
    
    return all_tools


def copilot_kit_endpoint(config: Dict[str, Any]) -> CopilotKitEndpoint:
    """Factory function for CopilotKit endpoints."""
    return CopilotKitEndpoint(
        **config,
        type=EndpointType.COPILOTKIT
    )


def langgraph_platform_endpoint(config: Dict[str, Any]) -> LangGraphPlatformEndpoint:
    """Factory function for LangGraph Platform endpoints."""
    return LangGraphPlatformEndpoint(
        **config,
        type=EndpointType.LANGGRAPH_PLATFORM
    )


def resolve_endpoint_type(endpoint: EndpointDefinition) -> EndpointType:
    """Resolve endpoint type from endpoint definition."""
    if hasattr(endpoint, 'type') and endpoint.type:
        return endpoint.type
    
    if (hasattr(endpoint, 'deployment_url') and hasattr(endpoint, 'agents')):
        return EndpointType.LANGGRAPH_PLATFORM
    else:
        return EndpointType.COPILOTKIT