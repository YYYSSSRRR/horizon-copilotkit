"""
FastAPI集成实现。
"""

from typing import Any, Dict, List, Optional, AsyncIterator
import json
import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..runtime import CopilotRuntime
from ..types.adapters import CopilotServiceAdapter
from ..types.runtime import CopilotRuntimeRequest, RequestContext
from ..types.messages import Message, TextMessage, ActionExecutionMessage, ResultMessage, MessageRole, convert_json_to_messages, convert_messages_to_json
from ..types.actions import ActionResult
from ..events.runtime_events import RuntimeEvent, RuntimeEventSource
from ..utils.common import generate_id

logger = logging.getLogger(__name__)


# 请求/响应模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[Dict[str, Any]] = Field(..., description="消息列表")
    thread_id: Optional[str] = Field(None, alias="threadId", description="线程ID")
    run_id: Optional[str] = Field(None, alias="runId", description="运行ID")
    stream: bool = Field(False, description="是否流式响应")
    model: Optional[str] = Field(None, description="模型名称")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="动作列表")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展信息")
    agent_session: Optional[Dict[str, Any]] = Field(None, alias="agentSession", description="代理会话信息")
    forwarded_parameters: Optional[Dict[str, Any]] = Field(None, alias="forwardedParameters", description="转发参数")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class ChatResponse(BaseModel):
    """聊天响应模型"""
    thread_id: str = Field(..., alias="threadId", description="线程ID")
    run_id: Optional[str] = Field(None, alias="runId", description="运行ID")
    messages: List[Dict[str, Any]] = Field(..., description="响应消息")
    timestamp: str = Field(..., description="时间戳")
    extensions: Optional[Dict[str, Any]] = Field(None, description="扩展信息")
    status: Dict[str, Any] = Field(default_factory=lambda: {"code": "success"}, description="状态信息")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class ActionExecuteRequest(BaseModel):
    """动作执行请求模型"""
    action_name: str = Field(..., alias="name", description="动作名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="动作参数")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class ActionExecuteResponse(BaseModel):
    """动作执行响应模型"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, alias="executionTime", description="执行时间")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class AgentInfo(BaseModel):
    """代理信息模型"""
    name: str = Field(..., description="代理名称")
    id: str = Field(..., description="代理ID")
    description: Optional[str] = Field(None, description="代理描述")
    configuration: Optional[Dict[str, Any]] = Field(None, description="代理配置")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class AgentStateRequest(BaseModel):
    """代理状态请求模型"""
    agent_name: str = Field(..., alias="agentName", description="代理名称")
    thread_id: str = Field(..., alias="threadId", description="线程ID")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class AgentStateResponse(BaseModel):
    """代理状态响应模型"""
    agent_name: str = Field(..., alias="agentName", description="代理名称")
    thread_id: str = Field(..., alias="threadId", description="线程ID")
    state: Any = Field(..., description="代理状态")
    running: bool = Field(..., description="是否运行中")
    node_name: Optional[str] = Field(None, alias="nodeName", description="节点名称")
    run_id: Optional[str] = Field(None, alias="runId", description="运行ID")
    active: bool = Field(..., description="是否活跃")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")
    version: str = Field(..., description="版本")
    provider: Optional[str] = Field(None, description="提供商")
    model: Optional[str] = Field(None, description="模型")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class CopilotRuntimeServer:
    """
    CopilotKit运行时服务器
    
    提供REST API接口，包括：
    - 聊天端点（支持流式响应）
    - 动作执行端点
    - 健康检查端点
    - 代理管理端点
    """
    
    def __init__(
        self,
        runtime: CopilotRuntime,
        service_adapter: CopilotServiceAdapter,
        title: str = "CopilotKit Runtime",
        version: str = "1.8.15-next.0",
        cors_origins: List[str] = None,
        **kwargs
    ):
        """
        初始化服务器
        
        Args:
            runtime: CopilotRuntime实例
            service_adapter: 服务适配器
            title: API标题
            version: API版本
            cors_origins: CORS允许的源
            **kwargs: 其他FastAPI参数
        """
        self.runtime = runtime
        self.service_adapter = service_adapter
        self.version = version
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title=title,
            version=version,
            description="CopilotKit Runtime API - Python implementation without GraphQL",
            **kwargs
        )
        
        # 设置CORS
        if cors_origins is None:
            cors_origins = ["*"]  # 开发环境默认允许所有源
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"CopilotRuntimeServer initialized: {title} v{version}")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/api/health", response_model=HealthResponse)
        async def health_check():
            """健康检查端点"""
            provider = self.service_adapter.get_provider_name() if hasattr(self.service_adapter, "get_provider_name") else None
            model = self.service_adapter.get_model_name() if hasattr(self.service_adapter, "get_model_name") else None
            
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version=self.version,
                provider=provider,
                model=model
            )
        
        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat_completion(request: ChatRequest):
            """聊天完成端点（非流式）"""
            try:
                thread_id = request.thread_id or generate_id()
                run_id = request.run_id or generate_id()
                
                # 转换消息
                messages = convert_json_to_messages(request.messages)
                
                # 创建运行时请求
                runtime_request = CopilotRuntimeRequest(
                    service_adapter=self.service_adapter,
                    messages=messages,
                    thread_id=thread_id,
                    run_id=run_id,
                    context=RequestContext(
                        properties=request.context or {},
                        url=None
                    )
                )
                
                # 处理请求
                runtime_response = await self.runtime.process_runtime_request(runtime_request)
                
                # 等待事件完成并收集响应消息
                response_messages = await self._collect_response_messages(
                    runtime_response.event_source, 
                    runtime_response.server_side_actions,
                    thread_id
                )
                
                return ChatResponse(
                    threadId=runtime_response.thread_id,
                    runId=runtime_response.run_id,
                    messages=convert_messages_to_json(response_messages),
                    timestamp=datetime.now().isoformat(),
                    extensions=request.extensions
                )
                
            except Exception as e:
                logger.error(f"Error in chat completion: {e}")
                return ChatResponse(
                    threadId=thread_id,
                    messages=[],
                    timestamp=datetime.now().isoformat(),
                    status={"code": "error", "reason": str(e)}
                )
        
        @self.app.post("/api/chat/stream")
        async def chat_stream(request: ChatRequest):
            """聊天流式端点"""
            try:
                thread_id = request.thread_id or generate_id()
                run_id = request.run_id or generate_id()
                
                # 转换消息
                messages = convert_json_to_messages(request.messages)
                
                # 创建运行时请求
                runtime_request = CopilotRuntimeRequest(
                    service_adapter=self.service_adapter,
                    messages=messages,
                    thread_id=thread_id,
                    run_id=run_id,
                    context=RequestContext(
                        properties=request.context or {},
                        url=None
                    )
                )
                
                # 处理请求
                runtime_response = await self.runtime.process_runtime_request(runtime_request)
                
                # 创建流式响应
                return StreamingResponse(
                    self._create_event_stream(runtime_response.event_source, thread_id, run_id),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
                    }
                )
                
            except Exception as e:
                logger.error(f"Error in chat stream: {e}")
                error_event = RuntimeEvent(
                    type="error",
                    data={"error": str(e), "threadId": thread_id}
                )
                
                async def error_stream():
                    yield f"data: {error_event.to_json()}\n\n"
                    yield "data: [DONE]\n\n"
                
                return StreamingResponse(
                    error_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
        
        @self.app.get("/api/actions")
        async def list_actions():
            """列出可用动作"""
            try:
                # 创建一个临时请求来获取动作
                runtime_request = CopilotRuntimeRequest(
                    service_adapter=self.service_adapter,
                    messages=[],
                    context=RequestContext()
                )
                
                actions = await self.runtime._get_server_side_actions(runtime_request)
                
                return {
                    "actions": [
                        {
                            "name": action.name,
                            "description": action.description,
                            "parameters": [param.dict() for param in action.parameters],
                            "available": "enabled"  # 服务器端动作始终可用
                        }
                        for action in actions
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error listing actions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/actions/execute", response_model=ActionExecuteResponse)
        async def execute_action(request: ActionExecuteRequest):
            """执行动作"""
            try:
                result = await self.runtime.execute_action(
                    request.action_name,
                    request.arguments
                )
                
                return ActionExecuteResponse(
                    success=result.success,
                    result=result.result,
                    error=result.error,
                    executionTime=result.execution_time
                )
                
            except Exception as e:
                logger.error(f"Error executing action: {e}")
                return ActionExecuteResponse(
                    success=False,
                    error=str(e)
                )
        
        @self.app.get("/api/agents")
        async def list_agents():
            """列出可用代理"""
            try:
                agents = await self.runtime.get_available_agents()
                
                return {
                    "agents": [
                        AgentInfo(
                            name=agent.name,
                            id=agent.id,
                            description=agent.description,
                            configuration=getattr(agent, "configuration", None)
                        ).dict(by_alias=True)
                        for agent in agents
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/agents/{agent_name}/state")
        async def get_agent_state(agent_name: str, thread_id: str):
            """获取代理状态"""
            try:
                state = await self.runtime.load_agent_state(agent_name, thread_id)
                
                if state is None:
                    return AgentStateResponse(
                        agentName=agent_name,
                        threadId=thread_id,
                        state={},
                        running=False,
                        active=False
                    )
                
                return AgentStateResponse(
                    agentName=agent_name,
                    threadId=thread_id,
                    state=state.state,
                    running=state.running,
                    nodeName=state.node_name,
                    runId=state.run_id,
                    active=state.active
                )
                
            except Exception as e:
                logger.error(f"Error getting agent state: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_name}/state")
        async def update_agent_state(agent_name: str, request: Dict[str, Any]):
            """更新代理状态"""
            try:
                thread_id = request.get("threadId")
                state = request.get("state", {})
                
                if not thread_id:
                    raise HTTPException(status_code=400, detail="threadId is required")
                
                await self.runtime.save_agent_state(agent_name, thread_id, state)
                
                return {
                    "agentName": agent_name,
                    "threadId": thread_id,
                    "state": state,
                    "running": True,
                    "active": True
                }
                
            except Exception as e:
                logger.error(f"Error updating agent state: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/")
        async def root():
            """根端点"""
            return {
                "name": "CopilotKit Runtime",
                "version": self.version,
                "description": "Python runtime for CopilotKit without GraphQL dependencies",
                "endpoints": {
                    "health": "/api/health",
                    "chat": "/api/chat",
                    "chat_stream": "/api/chat/stream",
                    "actions": "/api/actions",
                    "execute_action": "/api/actions/execute",
                    "agents": "/api/agents"
                }
            }
    
    async def _collect_response_messages(
        self, 
        event_source: RuntimeEventSource,
        server_side_actions: List = None,
        thread_id: str = None
    ) -> List[Message]:
        """
        收集响应消息（非流式）
        
        Args:
            event_source: 事件源
            
        Returns:
            消息列表
        """
        messages = []
        current_message = None
        current_action_execution = None
        action_executions = {}  # 存储动作执行信息
        action_args_buffers = {}  # 存储参数累积缓冲区
        
        # 等待一段时间收集事件
        await asyncio.sleep(0.1)
        
        events = event_source.get_events()
        for event in events:
            # 处理文本消息事件
            if event.type == "text_message_start":
                current_message = TextMessage(
                    role=MessageRole.ASSISTANT,
                    content=""
                )
            elif event.type == "text_message_content" and current_message:
                content = event.data.get("content", "")
                current_message.content += content
            elif event.type == "text_message_end" and current_message:
                messages.append(current_message)
                current_message = None
            
            # 处理动作执行事件
            elif event.type == "action_execution_start":
                action_execution_id = event.data.get("actionExecutionId")
                action_name = event.data.get("actionName", "")
                parent_message_id = event.data.get("parentMessageId")
                
                if action_execution_id:
                    current_action_execution = ActionExecutionMessage(
                        id=action_execution_id,
                        name=action_name,
                        arguments={},
                        parent_message_id=parent_message_id
                    )
                    action_executions[action_execution_id] = current_action_execution
                    action_args_buffers[action_execution_id] = ""  # 初始化参数缓冲区
            
            elif event.type == "action_execution_args":
                action_execution_id = event.data.get("actionExecutionId")
                args = event.data.get("args", "")
                
                if action_execution_id and action_execution_id in action_executions:
                    # 累积参数到缓冲区（处理增量式参数）
                    if action_execution_id not in action_args_buffers:
                        action_args_buffers[action_execution_id] = ""
                    
                    action_args_buffers[action_execution_id] += str(args)
                    
                    # 尝试解析累积的参数
                    accumulated_args = action_args_buffers[action_execution_id].strip()
                    if accumulated_args:
                        try:
                            # 尝试解析完整的JSON
                            if isinstance(accumulated_args, str):
                                parsed_args = json.loads(accumulated_args)
                            elif isinstance(args, dict):
                                parsed_args = args
                            else:
                                continue
                            
                            # 成功解析，更新参数
                            if isinstance(parsed_args, dict):
                                action_executions[action_execution_id].arguments.update(parsed_args)
                                # 清空缓冲区，表示已成功处理
                                action_args_buffers[action_execution_id] = ""
                            else:
                                # 如果解析出来的不是字典，存储为特殊键
                                action_executions[action_execution_id].arguments["parsed_value"] = parsed_args
                                action_args_buffers[action_execution_id] = ""
                                
                        except json.JSONDecodeError:
                            # JSON 还不完整，继续累积
                            # 但如果缓冲区太大，可能是格式错误，存储为原始参数
                            if len(accumulated_args) > 10000:  # 10KB 限制
                                action_executions[action_execution_id].arguments["raw_args"] = accumulated_args
                                action_args_buffers[action_execution_id] = ""
            
            elif event.type == "action_execution_end":
                action_execution_id = event.data.get("actionExecutionId")
                
                if action_execution_id and action_execution_id in action_executions:
                    # 处理任何剩余的缓冲区内容
                    if action_execution_id in action_args_buffers:
                        remaining_args = action_args_buffers[action_execution_id].strip()
                        if remaining_args:
                            # 尝试最后一次解析
                            try:
                                parsed_args = json.loads(remaining_args)
                                if isinstance(parsed_args, dict):
                                    action_executions[action_execution_id].arguments.update(parsed_args)
                                else:
                                    action_executions[action_execution_id].arguments["final_parsed_value"] = parsed_args
                            except json.JSONDecodeError:
                                # 最终解析失败，存储为原始参数
                                action_executions[action_execution_id].arguments["raw_args"] = remaining_args
                        
                        # 清理缓冲区
                        del action_args_buffers[action_execution_id]
                    
                    # 添加动作执行消息到结果中
                    action_execution_msg = action_executions[action_execution_id]
                    messages.append(action_execution_msg)
                    
                    # 执行服务器端动作
                    if server_side_actions and thread_id:
                        result_message = await self._execute_server_side_action(
                            action_execution_msg, server_side_actions, thread_id
                        )
                        if result_message:
                            messages.append(result_message)
                    
                    current_action_execution = None
            
            # 处理其他通用事件类型（兼容性）
            elif event.type == "message_start":
                current_message = TextMessage(
                    role=MessageRole.ASSISTANT,
                    content=""
                )
            elif event.type == "text_delta" and current_message:
                delta = event.data.get("delta", "")
                current_message.content += delta
            elif event.type == "message_end" and current_message:
                messages.append(current_message)
                current_message = None
        
        # 如果还有未完成的消息
        if current_message:
            messages.append(current_message)
        
        # 如果还有未完成的动作执行
        if current_action_execution:
            messages.append(current_action_execution)
        
        return messages
    
    async def _execute_server_side_action(
        self, 
        action_execution_msg: ActionExecutionMessage,
        server_side_actions: List,
        thread_id: str
    ) -> Optional[ResultMessage]:
        """
        执行服务器端动作
        
        Args:
            action_execution_msg: 动作执行消息
            server_side_actions: 服务器端动作列表
            thread_id: 线程ID
            
        Returns:
            结果消息，如果执行失败返回None
        """
        # 查找对应的动作
        action = None
        for server_action in server_side_actions:
            if hasattr(server_action, 'name') and server_action.name == action_execution_msg.name:
                action = server_action
                break
        
        if not action:
            logger.warning(f"Server-side action '{action_execution_msg.name}' not found")
            return None
        
        try:
            # 执行动作
            result = await self.runtime.execute_action(
                action_execution_msg.name, 
                action_execution_msg.arguments
            )
            
            # 创建结果消息
            result_message = ResultMessage(
                id=f"result-{action_execution_msg.id}",
                action_execution_id=action_execution_msg.id,
                action_name=action_execution_msg.name,
                result=result.result if result.success else f"Error: {result.error}"
            )
            
            logger.info(f"✅ [FastAPI] Action '{action_execution_msg.name}' executed successfully")
            return result_message
            
        except Exception as e:
            logger.error(f"❌ [FastAPI] Error executing action '{action_execution_msg.name}': {e}")
            
            # 创建错误结果消息
            error_result_message = ResultMessage(
                id=f"result-{action_execution_msg.id}",
                action_execution_id=action_execution_msg.id,
                action_name=action_execution_msg.name,
                result=f"Error: {str(e)}"
            )
            
            return error_result_message
    
    async def _create_event_stream(
        self, 
        event_source: RuntimeEventSource, 
        thread_id: str,
        run_id: str
    ) -> AsyncIterator[str]:
        """
        创建事件流（实现动作执行逻辑）
        
        Args:
            event_source: 事件源
            thread_id: 线程ID
            run_id: 运行ID
            
        Yields:
            SSE格式的事件字符串
        """
        try:
            # 发送会话开始事件
            session_start = {
                "type": "session_start",
                "data": {
                    "threadId": thread_id,
                    "runId": run_id
                }
            }
            yield f"data: {json.dumps(session_start)}\n\n"
            
            # 获取服务器端动作列表
            try:
                runtime_request = CopilotRuntimeRequest(
                    service_adapter=self.service_adapter,
                    messages=[],
                    thread_id=thread_id,
                    run_id=run_id,
                    context=RequestContext()
                )
                server_side_actions = await self.runtime._get_server_side_actions(runtime_request)
            except Exception as e:
                logger.error(f"Failed to get server side actions: {e}")
                server_side_actions = []
            
            # 开始流式传输
            await event_source.start_streaming()
            
            # 状态跟踪（类似 TypeScript 版本）
            action_state = {
                "callActionServerSide": False,
                "args": "",
                "actionExecutionId": None,
                "action": None,
                "actionExecutionParentMessageId": None,
            }
            
            # 创建真正的异步事件迭代器
            async def real_event_iterator():
                """真正的异步事件迭代器，实时获取事件"""
                # 首先发送已有的事件
                existing_events = event_source.get_events()
                for event in existing_events:
                    yield event
                
                # 然后监听新事件（实时流式处理）
                event_queue = asyncio.Queue()
                
                # 注册回调以接收新事件
                async def event_callback(event_iter):
                    async for event in event_iter:
                        await event_queue.put(event)
                
                event_source.stream(event_callback)
                
                # 监听队列中的新事件
                while event_source._streaming:
                    try:
                        # 等待新事件，设置超时避免永久阻塞
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                        yield event
                    except asyncio.TimeoutError:
                        # 超时继续循环，检查是否还在流式传输
                        continue
                    except Exception as e:
                        logger.error(f"Error in event queue: {e}")
                        break
            
            # 流式发送事件，并处理动作执行
            async for event in real_event_iterator():
                # 更新动作状态
                if event.type == "action_execution_start":
                    action_name = event.data.get("actionName")
                    action_state["callActionServerSide"] = any(
                        action.name == action_name for action in server_side_actions
                    )
                    action_state["args"] = ""
                    action_state["actionExecutionId"] = event.data.get("actionExecutionId")
                    if action_state["callActionServerSide"]:
                        action_state["action"] = next(
                            (action for action in server_side_actions if action.name == action_name),
                            None
                        )
                    action_state["actionExecutionParentMessageId"] = event.data.get("parentMessageId")
                
                elif event.type == "action_execution_args":
                    action_state["args"] += event.data.get("args", "")
                
                elif event.type == "action_execution_end" and action_state["callActionServerSide"]:
                    # 执行服务器端动作（类似 TypeScript 版本的 executeAction）
                    try:
                        # 解析参数
                        args = {}
                        if action_state["args"]:
                            try:
                                args = json.loads(action_state["args"])
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse action arguments: {action_state['args']}")
                        
                        # 执行动作
                        action = action_state["action"]
                        result = await self.runtime.execute_action(action.name, args)
                        
                        # 发送动作执行结果事件
                        action_result_event = {
                            "type": "action_execution_result",
                            "data": {
                                "actionExecutionId": action_state["actionExecutionId"],
                                "actionName": action.name,
                                "result": result.result if result.success else None,
                                "error": result.error if not result.success else None,
                                "success": result.success
                            }
                        }
                        
                        # 先发送原始事件
                        sse_data = f"data: {event.to_json()}\n\n"
                        yield sse_data
                        
                        # 然后发送执行结果事件
                        result_sse_data = f"data: {json.dumps(action_result_event)}\n\n"
                        yield result_sse_data
                        
                        logger.info(f"✅ [Stream] Action '{action.name}' executed and result sent")
                        continue  # 跳过下面的常规事件发送
                        
                    except Exception as e:
                        logger.error(f"❌ [Stream] Error executing action: {e}")
                        
                        # 发送错误结果事件
                        error_result_event = {
                            "type": "action_execution_result",
                            "data": {
                                "actionExecutionId": action_state["actionExecutionId"],
                                "actionName": action_state["action"].name if action_state["action"] else "unknown",
                                "result": None,
                                "error": str(e),
                                "success": False
                            }
                        }
                        
                        # 先发送原始事件
                        sse_data = f"data: {event.to_json()}\n\n"
                        yield sse_data
                        
                        # 然后发送错误结果事件
                        error_sse_data = f"data: {json.dumps(error_result_event)}\n\n"
                        yield error_sse_data
                        continue  # 跳过下面的常规事件发送
                
                # 发送常规事件
                sse_data = f"data: {event.to_json()}\n\n"
                yield sse_data
            
            # 发送会话结束事件
            session_end = {
                "type": "session_end",
                "data": {
                    "threadId": thread_id,
                    "runId": run_id
                }
            }
            yield f"data: {json.dumps(session_end)}\n\n"
            
            # 发送结束信号
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            error_event = RuntimeEvent(
                type="error",
                data={"error": str(e), "threadId": thread_id}
            )
            yield f"data: {error_event.to_json()}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await event_source.stop_streaming()
    
    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        **kwargs
    ):
        """
        运行服务器
        
        Args:
            host: 主机地址
            port: 端口号
            **kwargs: uvicorn参数
        """
        logger.info(f"Starting CopilotKit Runtime Server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            **kwargs
        )


def create_copilot_app(
    runtime: CopilotRuntime,
    service_adapter: CopilotServiceAdapter,
    **kwargs
) -> FastAPI:
    """
    创建CopilotKit FastAPI应用的便捷函数
    
    Args:
        runtime: CopilotRuntime实例
        service_adapter: 服务适配器
        **kwargs: CopilotRuntimeServer参数
        
    Returns:
        FastAPI应用实例
    """
    server = CopilotRuntimeServer(runtime, service_adapter, **kwargs)
    return server.app 