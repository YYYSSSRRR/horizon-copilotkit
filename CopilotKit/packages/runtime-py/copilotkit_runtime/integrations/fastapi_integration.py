"""
FastAPI集成实现。

参考runtime-next版本的接口设计，但适配Python的runtime-py架构。
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

from ..core.copilot_runtime import CopilotRuntime
from ..types.adapters import CopilotServiceAdapter
from ..types.runtime import CopilotRuntimeRequest, CopilotResponse
from ..types.messages import Message, TextMessage, ActionExecutionMessage, ResultMessage, MessageRole
from ..types.actions import ActionResult
from ..types.events import RuntimeEvent, RuntimeEventSource
from ..utils.helpers import random_id

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
        
        # 配置服务适配器
        self.runtime.use(service_adapter)
        
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
        
        logger.info(f"🚀 [CopilotRuntimeServer] 初始化完成: {title} v{version}")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/api/health", response_model=HealthResponse)
        async def health_check():
            """健康检查端点"""
            provider = getattr(self.service_adapter, "provider", None)
            model = getattr(self.service_adapter, "model", None)
            
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
                thread_id = request.thread_id or random_id()
                run_id = request.run_id or random_id()
                
                # 转换消息格式
                messages = self._convert_json_to_messages(request.messages)
                
                # 创建运行时请求
                runtime_request = CopilotRuntimeRequest(
                    messages=messages,
                    thread_id=thread_id,
                    run_id=run_id,
                    context=request.context or {},
                    actions=request.actions or [],
                    extensions=request.extensions or {}
                )
                
                # 处理请求
                response = await self.runtime.process_request(runtime_request)
                
                # 等待响应完成并收集消息
                response_messages = await self._collect_response_messages(response)
                
                return ChatResponse(
                    threadId=thread_id,
                    runId=run_id,
                    messages=self._convert_messages_to_json(response_messages),
                    timestamp=datetime.now().isoformat(),
                    extensions=request.extensions
                )
                
            except Exception as e:
                logger.error(f"❌ [Chat] 聊天完成错误: {e}")
                return ChatResponse(
                    threadId=thread_id or random_id(),
                    runId=run_id or random_id(),
                    messages=[],
                    timestamp=datetime.now().isoformat(),
                    status={"code": "error", "reason": str(e)}
                )
        
        @self.app.post("/api/chat/stream")
        async def chat_stream(request: ChatRequest):
            """聊天流式端点"""
            try:
                thread_id = request.thread_id or random_id()
                run_id = request.run_id or random_id()
                
                # 转换消息格式
                messages = self._convert_json_to_messages(request.messages)
                
                # 创建运行时请求
                runtime_request = CopilotRuntimeRequest(
                    messages=messages,
                    thread_id=thread_id,
                    run_id=run_id,
                    context=request.context or {},
                    actions=request.actions or [],
                    extensions=request.extensions or {}
                )
                
                # 处理请求
                response = await self.runtime.process_request(runtime_request)
                
                # 创建流式响应
                return StreamingResponse(
                    self._create_event_stream(response, thread_id, run_id),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
                    }
                )
                
            except Exception as e:
                logger.error(f"❌ [Stream] 流式聊天错误: {e}")
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
                actions = self.runtime.get_actions()
                
                return {
                    "actions": [
                        {
                            "name": action.name,
                            "description": action.description,
                            "parameters": action.parameters,
                            "available": "enabled"  # 服务器端动作始终可用
                        }
                        for action in actions
                    ]
                }
                
            except Exception as e:
                logger.error(f"❌ [Actions] 列出动作错误: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/actions/execute", response_model=ActionExecuteResponse)
        async def execute_action(request: ActionExecuteRequest):
            """执行动作"""
            try:
                import time
                start_time = time.time()
                
                # 执行动作
                result = await self.runtime.execute_action(
                    request.action_name,
                    request.arguments
                )
                
                execution_time = time.time() - start_time
                
                return ActionExecuteResponse(
                    success=result.success if hasattr(result, 'success') else True,
                    result=result.result if hasattr(result, 'result') else result,
                    error=result.error if hasattr(result, 'error') else None,
                    executionTime=execution_time
                )
                
            except Exception as e:
                logger.error(f"❌ [Action] 执行动作错误: {e}")
                return ActionExecuteResponse(
                    success=False,
                    error=str(e)
                )
        
        @self.app.get("/api/agents")
        async def list_agents():
            """列出可用代理"""
            try:
                # 目前Python版本暂不支持代理，返回空列表
                return {"agents": []}
                
            except Exception as e:
                logger.error(f"❌ [Agents] 列出代理错误: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/agents/{agent_name}/state")
        async def get_agent_state(agent_name: str, thread_id: str):
            """获取代理状态"""
            try:
                # 目前Python版本暂不支持代理状态
                return AgentStateResponse(
                    agentName=agent_name,
                    threadId=thread_id,
                    state={},
                    running=False,
                    active=False
                )
                
            except Exception as e:
                logger.error(f"❌ [Agent] 获取代理状态错误: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_name}/state")
        async def update_agent_state(agent_name: str, request: Dict[str, Any]):
            """更新代理状态"""
            try:
                thread_id = request.get("threadId")
                state = request.get("state", {})
                
                if not thread_id:
                    raise HTTPException(status_code=400, detail="threadId is required")
                
                # 目前Python版本暂不支持代理状态更新
                return {
                    "agentName": agent_name,
                    "threadId": thread_id,
                    "state": state,
                    "running": False,
                    "active": False
                }
                
            except Exception as e:
                logger.error(f"❌ [Agent] 更新代理状态错误: {e}")
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
        
        logger.info("📝 [CopilotRuntimeServer] API路由注册完成")
    
    def _convert_json_to_messages(self, json_messages: List[Dict[str, Any]]) -> List[Message]:
        """将JSON消息转换为Message对象"""
        messages = []
        for msg_data in json_messages:
            role = MessageRole(msg_data.get("role", "user"))
            content = msg_data.get("content", "")
            
            if role == MessageRole.USER or role == MessageRole.ASSISTANT:
                message = TextMessage(
                    role=role,
                    content=content,
                    id=msg_data.get("id", random_id())
                )
            else:
                message = TextMessage(
                    role=role,
                    content=content,
                    id=msg_data.get("id", random_id())
                )
            
            messages.append(message)
        
        return messages
    
    def _convert_messages_to_json(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将Message对象转换为JSON格式"""
        json_messages = []
        for message in messages:
            msg_dict = {
                "id": getattr(message, "id", random_id()),
                "role": message.role.value,
                "content": message.content
            }
            
            # 添加特定类型的字段
            if isinstance(message, ActionExecutionMessage):
                msg_dict.update({
                    "type": "action_execution",
                    "name": message.name,
                    "arguments": message.arguments
                })
            elif isinstance(message, ResultMessage):
                msg_dict.update({
                    "type": "result",
                    "action_execution_id": message.action_execution_id,
                    "action_name": message.action_name,
                    "result": message.result
                })
            
            json_messages.append(msg_dict)
        
        return json_messages
    
    async def _collect_response_messages(self, response: CopilotResponse) -> List[Message]:
        """收集响应消息（非流式）"""
        messages = []
        
        if hasattr(response, 'messages') and response.messages:
            messages.extend(response.messages)
        
        # 如果有事件源，收集事件中的消息
        if hasattr(response, 'event_source') and response.event_source:
            event_messages = await self._collect_messages_from_events(response.event_source)
            messages.extend(event_messages)
        
        return messages
    
    async def _collect_messages_from_events(self, event_source: RuntimeEventSource) -> List[Message]:
        """从事件源收集消息"""
        messages = []
        current_message = None
        
        # 等待事件完成
        await asyncio.sleep(0.1)
        
        # 获取所有事件
        events = getattr(event_source, 'events', [])
        
        for event in events:
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
        
        # 如果有未完成的消息
        if current_message:
            messages.append(current_message)
        
        return messages
    
    async def _create_event_stream(
        self, 
        response: CopilotResponse, 
        thread_id: str,
        run_id: str
    ) -> AsyncIterator[str]:
        """
        创建事件流
        
        Args:
            response: 运行时响应
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
            server_side_actions = self.runtime.get_actions()
            
            # 状态跟踪
            action_state = {
                "callActionServerSide": False,
                "args": "",
                "actionExecutionId": None,
                "action": None,
                "actionExecutionParentMessageId": None,
            }
            
            # 如果响应有事件源，处理流式事件
            if hasattr(response, 'event_source') and response.event_source:
                event_source = response.event_source
                
                # 模拟事件流处理
                async def process_events():
                    events = getattr(event_source, 'events', [])
                    for event in events:
                        yield event
                
                # 处理每个事件
                async for event in process_events():
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
                        # 执行服务器端动作
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
                                    "result": result if not hasattr(result, 'result') else result.result,
                                    "error": None if not hasattr(result, 'error') else result.error,
                                    "success": True if not hasattr(result, 'success') else result.success
                                }
                            }
                            
                            # 先发送原始事件
                            sse_data = f"data: {json.dumps(event.to_dict())}\n\n"
                            yield sse_data
                            
                            # 然后发送执行结果事件
                            result_sse_data = f"data: {json.dumps(action_result_event)}\n\n"
                            yield result_sse_data
                            
                            logger.info(f"✅ [Stream] 动作 '{action.name}' 执行完成并发送结果")
                            continue
                            
                        except Exception as e:
                            logger.error(f"❌ [Stream] 执行动作错误: {e}")
                            
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
                            sse_data = f"data: {json.dumps(event.to_dict())}\n\n"
                            yield sse_data
                            
                            # 然后发送错误结果事件
                            error_sse_data = f"data: {json.dumps(error_result_event)}\n\n"
                            yield error_sse_data
                            continue
                    
                    # 发送常规事件
                    sse_data = f"data: {json.dumps(event.to_dict())}\n\n"
                    yield sse_data
            
            # 如果响应有直接消息，发送它们
            if hasattr(response, 'messages') and response.messages:
                for message in response.messages:
                    message_event = {
                        "type": "message",
                        "data": {
                            "role": message.role.value,
                            "content": message.content,
                            "id": getattr(message, "id", random_id())
                        }
                    }
                    yield f"data: {json.dumps(message_event)}\n\n"
            
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
            logger.error(f"❌ [Stream] 事件流错误: {e}")
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
        logger.info(f"🚀 [Server] 启动CopilotKit Runtime服务器: {host}:{port}")
        
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


def create_copilot_runtime_server(
    runtime: CopilotRuntime,
    service_adapter: CopilotServiceAdapter,
    **kwargs
) -> CopilotRuntimeServer:
    """
    创建CopilotRuntimeServer实例
    
    兼容runtime-next的创建方式
    """
    return CopilotRuntimeServer(runtime, service_adapter, **kwargs) 