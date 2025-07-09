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
from ..types.messages import Message, TextMessage, MessageRole, convert_json_to_messages, convert_messages_to_json
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
                response_messages = await self._collect_response_messages(runtime_response.event_source)
                
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
    
    async def _collect_response_messages(self, event_source: RuntimeEventSource) -> List[Message]:
        """
        收集响应消息（非流式）
        
        Args:
            event_source: 事件源
            
        Returns:
            消息列表
        """
        messages = []
        current_message = None
        
        # 等待一段时间收集事件
        await asyncio.sleep(0.1)
        
        events = event_source.get_events()
        for event in events:
            if event.type == "message_start":
                current_message = TextMessage(
                    role=MessageRole.ASSISTANT,
                    content=""
                )
            elif event.type == "text_delta" and current_message:
                current_message.content += event.data.get("delta", "")
            elif event.type == "message_end" and current_message:
                messages.append(current_message)
                current_message = None
        
        # 如果还有未完成的消息
        if current_message:
            messages.append(current_message)
        
        return messages
    
    async def _create_event_stream(
        self, 
        event_source: RuntimeEventSource, 
        thread_id: str,
        run_id: str
    ) -> AsyncIterator[str]:
        """
        创建事件流
        
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
            
            # 开始流式传输
            await event_source.start_streaming()
            
            # 创建事件迭代器
            async def event_iterator():
                events = event_source.get_events()
                for event in events:
                    yield event
            
            # 流式发送事件
            async for event in event_iterator():
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