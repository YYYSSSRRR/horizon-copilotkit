"""
FastAPI 集成实现。
参考 runtime-next 的实现，提供 create_copilot_app API。
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
import structlog

from ...lib.types import Message, ActionInput, ActionResult, Role, RuntimeEventSource
from ...service_adapters.base import ServiceAdapter, CopilotServiceAdapter
from ...api.models.requests import GenerateCopilotResponseInput, ForwardedParametersInput, ExtensionsInput, AgentSessionInput, AgentStateInput
from ...api.handlers.copilot_handler import CopilotHandlerComplete
from ...api.models.responses import CopilotResponse
from ...lib.runtime.copilot_runtime import CopilotRuntime
from ...lib.events import RuntimeEventSource as NewRuntimeEventSource, RuntimeEventSubject, create_fastapi_event_data, observable_to_async_generator

logger = structlog.get_logger(__name__)


class FastAPIEventSource(NewRuntimeEventSource):
    """
    FastAPI 事件源适配器，将 RuntimeEventSource 事件转换为 FastAPI 流式响应格式
    
    这个类继承自新的 RuntimeEventSource 并重写 stream 方法，
    将事件转换为 FastAPI 的 Server-Sent Events (SSE) 格式。
    """
    
    def __init__(self, yield_queue: List[str]):
        super().__init__()
        self.yield_queue = yield_queue
    
    async def stream(self, callback):
        """
        处理事件流并转换为 FastAPI 格式
        
        Args:
            callback: 事件处理回调函数
        """
        event_subject = RuntimeEventSubject()
        
        # 订阅事件并转换为 FastAPI 格式
        def event_handler(event):
            event_data = create_fastapi_event_data(event)
            sse_data = f"data: {json.dumps(event_data)}\n\n"
            self.yield_queue.append(sse_data)
        
        event_subject.subscribe(event_handler)
        
        # 设置事件流并调用回调
        self._event_stream = event_subject
        
        try:
            await callback(event_subject)
        except Exception as e:
            logger.error(f"Error in FastAPI event stream callback: {e}")
            self.send_error_message_to_chat()
            event_subject.on_completed()
    
    def send_error_message_to_chat(self, message: str = "An error occurred. Please try again."):
        """发送错误消息到聊天"""
        error_event = {
            "type": "error",
            "data": {
                "error": message,
                "timestamp": datetime.now().isoformat()
            }
        }
        self.yield_queue.append(f"data: {json.dumps(error_event)}\n\n")


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


class CopilotRuntimeChatCompletionRequest(BaseModel):
    """Request interface for chat completion using process method."""
    
    event_source: FastAPIEventSource
    messages: List[Message]
    actions: List[ActionInput]
    model: Optional[str] = None
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    forwarded_parameters: Optional[ForwardedParametersInput] = None
    extensions: Optional[ExtensionsInput] = None
    agent_session: Optional[AgentSessionInput] = None
    agent_states: Optional[List[AgentStateInput]] = None
    
    class Config:
        arbitrary_types_allowed = True


class CopilotRuntimeServer:
    """
    CopilotKit 运行时服务器
    
    提供 REST API 接口，包括：
    - 聊天端点（支持流式响应）
    - 动作执行端点
    - 健康检查端点
    - 代理管理端点
    """
    
    def __init__(
        self,
        runtime: CopilotRuntime,
        service_adapter: ServiceAdapter,
        title: str = "CopilotKit Runtime",
        version: str = "1.8.15-next.0",
        cors_origins: Optional[List[str]] = None,
        prefix: str = "",
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
            prefix: API路径前缀（例如 "/api/copilotkit"）
            **kwargs: 其他FastAPI参数
        """
        self.runtime = runtime
        self.service_adapter = service_adapter
        self.version = version
        self.prefix = prefix.rstrip('/')  # 移除末尾的斜杠
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title=title,
            version=version,
            description="CopilotKit Runtime API - Python implementation",
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
        
        @self.app.get(f"{self.prefix}/api/health", response_model=HealthResponse)
        async def health_check():
            """健康检查端点"""
            provider = getattr(self.service_adapter, 'provider', None)
            model = getattr(self.service_adapter, 'model', None)
            
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version=self.version,
                provider=provider,
                model=model
            )
        
        
        @self.app.get(f"{self.prefix}/copilotkit/agents")
        async def available_agents():
            """获取可用代理"""
            return {
                "agents": [
                    {
                        "name": "default",
                        "description": "默认助手代理",
                        "actions": self._get_available_actions()
                    }
                ]
            }
        
        @self.app.post(f"{self.prefix}/api/chat", response_model=ChatResponse)
        async def chat_completion(request: ChatRequest):
            """聊天完成端点（非流式）"""
            try:
                thread_id = request.thread_id or self._generate_id()
                run_id = request.run_id or self._generate_id()
                
                # 转换消息格式
                messages = self._convert_to_messages(request.messages)
                
                # 调用服务适配器（转换为字典格式）
                messages_dict = [{"role": str(msg.role), "content": msg.content} for msg in messages]
                actions_dict = [
                    {
                        "name": action.name,
                        "description": action.description,
                        "parameters": json.loads(action.json_schema) if action.json_schema else {}
                    }
                    for action in self._get_available_actions()
                ]
                response = await self.service_adapter.generate_response(
                    messages=messages_dict,
                    actions=actions_dict,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                # 处理响应 - generate_response 返回异步生成器，需要收集结果
                response_messages = []
                response_content = ""
                async for chunk in response:
                    if isinstance(chunk, dict) and chunk.get('type') == 'text_content':
                        response_content += chunk.get('content', '')
                
                if response_content:
                    response_messages.append({
                        "role": "assistant",
                        "content": response_content,
                        "id": f"msg_{datetime.now().timestamp()}"
                    })
                
                return ChatResponse(
                    threadId=thread_id,
                    runId=run_id,
                    messages=response_messages,
                    timestamp=datetime.now().isoformat(),
                    extensions=request.extensions or {}
                )
                
            except Exception as e:
                logger.error(f"Error in chat completion: {e}")
                return ChatResponse(
                    threadId=thread_id,
                    runId=run_id,
                    messages=[],
                    timestamp=datetime.now().isoformat(),
                    extensions={},
                    status={"code": "error", "reason": str(e)}
                )
        
        @self.app.post(f"{self.prefix}/api/chat/stream")
        async def chat_stream(request: ChatRequest, http_request: Request = None):
            """聊天流式端点"""
            try:
                thread_id = request.thread_id or self._generate_id()
                run_id = request.run_id or self._generate_id()
                
                # 转换消息格式
                messages = self._convert_to_messages(request.messages)
                
                # 创建流式响应
                return StreamingResponse(
                    self._create_event_stream(messages, thread_id, run_id, request, http_request),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "X-Accel-Buffering": "no"
                    }
                )
                
            except Exception as e:
                logger.error(f"Error in chat stream: {e}")
                error_message = str(e)
                
                async def error_stream():
                    error_event = {
                        "type": "error",
                        "data": {"error": error_message, "threadId": thread_id}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
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
        
        @self.app.get(f"{self.prefix}/" if self.prefix else "/")
        async def root():
            """根端点"""
            return {
                "name": "CopilotKit Runtime",
                "version": self.version,
                "description": "Python runtime for CopilotKit",
                "endpoints": {
                    "health": "/api/health",
                    "chat": "/api/chat",
                    "chat_stream": "/api/chat/stream",
                    "actions": "/api/actions",
                    "execute_action": "/api/actions/execute",
                    "copilotkit_hello": "/copilotkit/hello",
                    "copilotkit_agents": "/copilotkit/agents"
                }
            }
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _convert_to_messages(self, messages: List[Dict[str, Any]]) -> List[Message]:
        """转换消息格式 - 匹配前端扁平化消息结构，兼容 OpenAI 工具调用格式"""
        converted_messages = []
        
        logger.info(f"🔄 Converting {len(messages)} input messages to CopilotKit Message format")
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
                
            message_type = msg.get("type", "text")
            message_id = msg.get("id", f"msg_{i}_{datetime.now().timestamp()}")
            
            if message_type == "text":
                # 处理文本消息
                role = msg.get("role", "user")
                if role in ["user", "assistant", "system", "developer"]:  # 只处理有效角色
                    message = Message(
                        id=message_id,
                        role=role,
                        content=msg.get("content", ""),
                        text_content=msg.get("content", "")
                    )
                    converted_messages.append(message)
            
            elif message_type == "action_execution":
                # 处理动作执行消息 - 需要确保正确设置字段以便 is_action_execution_message() 返回 True
                message = Message(
                    id=message_id,
                    role="assistant",  # 动作执行消息必须是 assistant 角色
                    content="",  # 动作执行消息内容为空
                    name=msg.get("name", ""),  # 必须设置 name 字段
                    arguments=msg.get("arguments", {})  # 确保有 arguments 字段
                )
                converted_messages.append(message)
            
            elif message_type == "result":
                # 处理结果消息 - 需要确保正确设置字段以便 is_result_message() 返回 True
                message = Message(
                    id=message_id,
                    role="tool",  # 使用 tool 角色以匹配 TypeScript 版本
                    content=str(msg.get("result", "")),  # result 作为 content
                    result=str(msg.get("result", "")),  # 必须设置 result 字段
                    action_execution_id=msg.get("actionExecutionId", "")  # 必须设置 action_execution_id 字段
                )
                converted_messages.append(message)
            
            elif message_type == "agent_state":
                # 处理代理状态消息
                message = Message(
                    id=message_id,
                    role="assistant",
                    content="",  # 状态消息内容可以为空或存储状态信息
                )
                converted_messages.append(message)
            
            elif message_type == "image":
                # 处理图像消息
                message = Message(
                    id=message_id,
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    # 可以添加图像相关字段如果 Message 模型支持
                )
                converted_messages.append(message)
            
            else:
                # 未知类型，尝试作为文本消息处理（向后兼容）
                if "role" in msg and "content" in msg:
                    role = msg.get("role")
                    if role in ["user", "assistant", "system"]:
                        message = Message(
                            id=message_id,
                            role=role,
                            content=msg.get("content", ""),
                            text_content=msg.get("content", "")
                        )
                        converted_messages.append(message)
        
        logger.info(f"✅ Converted to {len(converted_messages)} CopilotKit messages:")
        for i, msg in enumerate(converted_messages):
            logger.info(f"  Message {i}: role={msg.role}, type={msg.__class__.__name__}, "
                       f"is_text={msg.is_text_message()}, is_action={msg.is_action_execution_message()}, "
                       f"is_result={msg.is_result_message()}, content_preview={str(msg.content)[:50]}...")
        
        return converted_messages
    
    def _get_available_actions(self) -> List[ActionInput]:
        """获取可用动作列表"""
        if isinstance(self.runtime.actions, list):
            return [
                ActionInput(
                    name=action.name,
                    description=action.description,
                    json_schema=json.dumps({
                        "type": "object",
                        "properties": {
                            param.name: {
                                "type": param.type,
                                "description": param.description
                            }
                            for param in (action.parameters or [])
                        },
                        "required": [param.name for param in (action.parameters or []) if param.required]
                    })
                )
                for action in self.runtime.actions
            ]
        return []
    
    async def _execute_action(self, action_name: str, arguments: Dict[str, Any]) -> Any:
        """执行动作"""
        if isinstance(self.runtime.actions, list):
            for action in self.runtime.actions:
                if action.name == action_name:
                    if hasattr(action, 'handler') and action.handler:
                        return await action.handler(arguments)
                    break
        
        raise ValueError(f"Action '{action_name}' not found or has no handler")
    
    async def _create_event_stream(
        self, 
        messages: List[Message], 
        thread_id: str,
        run_id: str,
        request: ChatRequest = None,
        http_request: Request = None
    ) -> AsyncIterator[str]:
        """创建事件流 - 使用 CopilotHandlerComplete.generate_copilot_response"""
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
            
            # 创建 CopilotHandlerComplete 实例
            context = {
                "_copilotkit": {
                    "runtime": self.runtime,
                    "service_adapter": self.service_adapter
                },
                "properties": {},
                "request": {
                    "headers": {}  # TODO: 从 FastAPI 请求中获取 headers
                }
            }
            
            copilot_handler = CopilotHandlerComplete(context)
            
            # 构造 GenerateCopilotResponseInput
            # 需要将 Message 转换为 MessageInput 格式，根据消息类型分别处理
            message_inputs = []
            for msg in messages:
                from ...api.models.messages import (
                    MessageInput, TextMessageInput, ActionExecutionMessageInput, 
                    ResultMessageInput
                )
                from ...api.models.enums import MessageRole
                
                message_input = None
                
                if msg.is_text_message():
                    # 处理文本消息
                    text_message = TextMessageInput(
                        id=msg.id,
                        content=str(msg.content),
                        role=MessageRole(msg.role)
                    )
                    message_input = MessageInput(text_message=text_message)
                
                elif msg.is_action_execution_message():
                    # 处理动作执行消息
                    action_message = ActionExecutionMessageInput(
                        id=msg.id,
                        name=msg.name or "",
                        arguments=json.dumps(msg.arguments or {})
                    )
                    message_input = MessageInput(action_execution_message=action_message)
                
                elif msg.is_result_message():
                    # 处理结果消息
                    result_message = ResultMessageInput(
                        id=msg.id,
                        action_execution_id=msg.action_execution_id or "",
                        action_name="",  # 这个字段在API模型中必需，但在转换中可能没有
                        result=msg.result or str(msg.content)
                    )
                    message_input = MessageInput(result_message=result_message)
                
                else:
                    # 默认作为文本消息处理
                    logger.warning(f"Unknown message type, treating as text: {msg}")
                    text_message = TextMessageInput(
                        id=msg.id,
                        content=str(msg.content),
                        role=MessageRole.USER  # 默认角色
                    )
                    message_input = MessageInput(text_message=text_message)
                
                if message_input:
                    message_inputs.append(message_input)
            
            # 导入必要的模型
            from ...api.models.requests import FrontendInput, GenerateCopilotResponseMetadataInput
            from ...api.models.enums import CopilotRequestType
            
            # 获取 frontend actions（从请求中的 actions 参数获取）
            frontend_actions = []
            if request and request.actions:
                # 转换 actions 格式以匹配 FrontendInput 的期望格式
                from ...api.models.requests import ActionInput as ActionInputModel
                for action in request.actions:
                    try:
                        # 转换 parameters 格式为 OpenAI 函数调用 schema 格式
                        parameters = action.get('parameters', {})
                        if isinstance(parameters, list):
                            # 如果 parameters 是列表格式，转换为 OpenAI schema 格式
                            properties = {}
                            required = []
                            for param in parameters:
                                if isinstance(param, dict) and 'name' in param:
                                    param_name = param['name']
                                    properties[param_name] = {
                                        'type': param.get('type', 'string'),
                                        'description': param.get('description', '')
                                    }
                                    if param.get('required', False):
                                        required.append(param_name)
                            
                            parameters = {
                                'type': 'object',
                                'properties': properties,
                                'required': required
                            }
                        
                        # 创建 ActionInput 实例
                        action_input = ActionInputModel(
                            name=action.get('name', ''),
                            description=action.get('description', ''),
                            parameters=parameters,
                            available=action.get('available', 'enabled')  # 默认为 enabled
                        )
                        frontend_actions.append(action_input)
                    except Exception as e:
                        logger.warning(f"Failed to convert action {action}: {e}")
                        continue
            
            # 获取 URL（从 HTTP headers 中获取）
            frontend_url = ""
            if http_request:
                # 尝试从常见的 headers 中获取前端 URL
                frontend_url = (
                    http_request.headers.get('origin', '') or
                    http_request.headers.get('referer', '') or
                    http_request.headers.get('x-forwarded-host', '') or
                    ""
                )
            
            frontend_input = FrontendInput(
                actions=frontend_actions,
                url=frontend_url
            )
            
            # 创建 metadata
            metadata = GenerateCopilotResponseMetadataInput(
                request_type=CopilotRequestType.CHAT
            )
            
            # 创建 GenerateCopilotResponseInput
            copilot_request = GenerateCopilotResponseInput(
                metadata=metadata,
                messages=message_inputs,
                frontend=frontend_input,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # 调用 generate_copilot_response 并流式输出
            async for sse_message in copilot_handler.generate_copilot_response(copilot_request):
                # 将 SSEMessage 转换为 FastAPI 格式
                # Parse the data to handle special events that need message format conversion
                try:
                    data_dict = json.loads(sse_message.data)
                    
                    # Convert certain events to proper frontend message format
                    if sse_message.event == "text_message_start":
                        # Add type field for text message start
                        data_dict["type"] = "text"
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event == "text_message_end":
                        # Text message end events are handled by create_fastapi_event_data
                        if data_dict.get("type") == "text_end":
                            yield f"data: {json.dumps(data_dict)}\n\n"
                        else:
                            # Skip old format text_message_end events
                            continue
                    elif sse_message.event == "text_message_content":
                        # Convert text_message_content to text_content format
                        if data_dict.get("type") == "text_content":
                            # Already in correct format
                            yield f"data: {json.dumps(data_dict)}\n\n"
                        else:
                            # Need to convert format
                            content_event = {
                                "type": "text_content",
                                "data": {
                                    "content": data_dict.get("content", ""),
                                    "messageId": data_dict.get("id", "")
                                }
                            }
                            yield f"data: {json.dumps(content_event)}\n\n"
                    elif data_dict.get("type") == "text_content":
                        # Forward text_content events directly (cumulative content)
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event in ["action_execution_start"]:
                        # Add type field for action execution messages
                        data_dict["type"] = "action_execution"
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event == "action_execution_args":
                        # Add type field for action execution args events
                        data_dict["type"] = "action_execution_args"
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event in ["action_execution_result"]:
                        # Add type field for result messages
                        data_dict["type"] = "result"
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event in ["agent_state_message"]:
                        # Add type field for agent state messages
                        data_dict["type"] = "agent_state"
                        yield f"data: {json.dumps(data_dict)}\n\n"
                    elif sse_message.event in ["response_start", "response_end", "meta_event", "error", "guardrails_failure"]:
                        # Skip these events as they're not frontend messages
                        continue
                    else:
                        # Default: output as-is with event type
                        yield f"event: {sse_message.event}\n"
                        yield f"data: {sse_message.data}\n\n"
                except json.JSONDecodeError:
                    # If data is not JSON, output as-is
                    yield f"event: {sse_message.event}\n"
                    yield f"data: {sse_message.data}\n\n"
            
            # 发送结束信号
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            error_event = {
                "type": "error",
                "data": {"error": str(e), "threadId": thread_id}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"
    
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
    service_adapter: ServiceAdapter,
    prefix: str = "",
    **kwargs
) -> FastAPI:
    """
    创建CopilotKit FastAPI应用的便捷函数
    
    Args:
        runtime: CopilotRuntime实例
        service_adapter: 服务适配器
        prefix: API路径前缀（例如 "/api/copilotkit"）
        **kwargs: CopilotRuntimeServer参数
        
    Returns:
        FastAPI应用实例
    """
    server = CopilotRuntimeServer(runtime, service_adapter, prefix=prefix, **kwargs)
    return server.app


# 兼容性函数
def setup_copilot_routes(app: FastAPI, runtime_context: Dict[str, Any]) -> None:
    """
    设置CopilotKit路由（兼容性函数）
    
    Args:
        app: FastAPI应用实例
        runtime_context: 运行时上下文
    """
    copilotkit_data = runtime_context.get("_copilotkit", {})
    runtime = copilotkit_data.get("runtime")
    service_adapter = copilotkit_data.get("service_adapter")
    
    if not runtime or not service_adapter:
        raise ValueError("Invalid runtime context")
    
    # 创建服务器实例并复制路由
    server = CopilotRuntimeServer(runtime, service_adapter)
    
    # 将路由添加到现有应用
    for route in server.app.routes:
        app.routes.append(route)


def fastapi_integration(app: FastAPI, copilot_runtime: CopilotRuntime, service_adapter: ServiceAdapter, **kwargs):
    """
    主要的FastAPI集成函数
    
    Args:
        app: FastAPI应用实例
        copilot_runtime: CopilotRuntime实例
        service_adapter: 服务适配器实例
        **kwargs: 其他配置选项
    """
    
    # 设置运行时上下文
    runtime_context = {
        "_copilotkit": {
            "runtime": copilot_runtime,
            "service_adapter": service_adapter,
            **kwargs
        },
        "properties": {},
        "logger": logger
    }
    
    # 设置路由
    setup_copilot_routes(app, runtime_context)
    
    logger.info("CopilotKit FastAPI integration setup completed")


# 兼容性别名
def copilotkit_fastapi(app: FastAPI, copilot_runtime: CopilotRuntime, service_adapter: Optional[ServiceAdapter] = None, **kwargs):
    """
    兼容性函数名称
    
    Args:
        app: FastAPI应用实例
        copilot_runtime: CopilotRuntime实例或配置字典
        service_adapter: 服务适配器实例（可选）
        **kwargs: 其他配置选项
    """
    
    # 处理不同的参数格式
    if isinstance(copilot_runtime, dict):
        service_adapter = copilot_runtime.get('service_adapter', service_adapter)
        copilot_runtime = copilot_runtime.get('runtime', copilot_runtime)
    
    if service_adapter is None:
        raise ValueError("service_adapter is required")
    
    return fastapi_integration(app, copilot_runtime, service_adapter, **kwargs)