"""
CopilotRuntime核心类

对标TypeScript的CopilotRuntime实现
"""

import logging
from typing import Any, Dict, List, Optional, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse

from ..types.adapters import CopilotServiceAdapter, EmptyAdapter
from ..types.actions import Action, ActionInput
from .copilot_resolver import CopilotResolver

logger = logging.getLogger(__name__)


class CopilotRuntime:
    """
    CopilotKit Python运行时
    
    对标TypeScript的CopilotRuntime类，提供完整的运行时功能
    """
    
    def __init__(self):
        self._service_adapter: Optional[CopilotServiceAdapter] = None
        self._actions: List[Action] = []
        self._middleware = []
        self._agent_endpoints = []
        self._app: Optional[FastAPI] = None
        self._resolver: Optional[CopilotResolver] = None
        
        logger.info("🚀 [CopilotRuntime] 初始化Python运行时")
    
    @property
    def app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        if self._app is None:
            self._app = self._create_fastapi_app()
        return self._app
    
    def use(self, adapter: CopilotServiceAdapter) -> "CopilotRuntime":
        """
        配置服务适配器
        
        Args:
            adapter: 服务适配器实例
            
        Returns:
            自身实例，支持链式调用
        """
        self._service_adapter = adapter
        logger.info(f"🔧 [CopilotRuntime] 配置服务适配器: {type(adapter).__name__}")
        return self
    
    def action(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None
    ) -> "CopilotRuntime":
        """
        注册动作
        
        Args:
            name: 动作名称
            description: 动作描述
            parameters: 参数schema
            handler: 处理函数
            
        Returns:
            自身实例，支持链式调用
        """
        action = Action(
            name=name,
            description=description,
            parameters=parameters or {},
            handler=handler
        )
        self._actions.append(action)
        logger.info(f"⚙️ [CopilotRuntime] 注册动作: {name}")
        return self
    
    def middleware(self, middleware_func: Callable) -> "CopilotRuntime":
        """
        添加中间件
        
        Args:
            middleware_func: 中间件函数
            
        Returns:
            自身实例，支持链式调用
        """
        self._middleware.append(middleware_func)
        logger.info(f"🔗 [CopilotRuntime] 添加中间件: {middleware_func.__name__}")
        return self
    
    def agent(self, endpoint: str, **kwargs) -> "CopilotRuntime":
        """
        配置代理端点
        
        Args:
            endpoint: 代理端点URL
            **kwargs: 其他配置参数
            
        Returns:
            自身实例，支持链式调用
        """
        agent_config = {"endpoint": endpoint, **kwargs}
        self._agent_endpoints.append(agent_config)
        logger.info(f"🤖 [CopilotRuntime] 配置代理端点: {endpoint}")
        return self
    
    def get_service_adapter(self) -> Optional[CopilotServiceAdapter]:
        """获取当前服务适配器"""
        return self._service_adapter
    
    def get_actions(self) -> List[Action]:
        """获取已注册的动作"""
        return self._actions.copy()
    
    def _create_fastapi_app(self) -> FastAPI:
        """创建FastAPI应用"""
        app = FastAPI(
            title="CopilotKit Python Runtime",
            description="CopilotKit的Python运行时，无GraphQL依赖",
            version="0.1.0"
        )
        
        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境中应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 创建解析器
        self._resolver = CopilotResolver(self)
        
        # 注册路由
        self._register_routes(app)
        
        logger.info("🌐 [CopilotRuntime] FastAPI应用创建完成")
        return app
    
    def _register_routes(self, app: FastAPI):
        """注册API路由"""
        
        @app.get("/")
        async def root():
            """根路径"""
            return {"message": "CopilotKit Python Runtime", "version": "0.1.0"}
        
        @app.get("/health")
        async def health():
            """健康检查"""
            return await self._resolver.hello()
        
        @app.get("/agents")
        async def available_agents():
            """获取可用代理"""
            return await self._resolver.available_agents()
        
        @app.post("/copilot/chat")
        async def chat_completion(request_data: Dict[str, Any]):
            """
            聊天完成接口
            
            对标GraphQL的generateCopilotResponse mutation
            """
            try:
                # 验证必要字段
                if "messages" not in request_data:
                    raise HTTPException(status_code=400, detail="缺少messages字段")
                
                # 使用流式响应
                return FastAPIStreamingResponse(
                    self._stream_chat_response(request_data),
                    media_type="application/json"
                )
            
            except Exception as e:
                logger.error(f"❌ [CopilotRuntime] 聊天完成处理失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/copilot/chat/stream")
        async def chat_completion_stream(request_data: Dict[str, Any]):
            """
            流式聊天完成接口
            
            使用Server-Sent Events (SSE)
            """
            try:
                return FastAPIStreamingResponse(
                    self._stream_chat_sse(request_data),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ [CopilotRuntime] SSE流处理失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/copilot/actions/execute")
        async def execute_action(action_data: Dict[str, Any]):
            """执行动作"""
            try:
                action_name = action_data.get("name")
                if not action_name:
                    raise HTTPException(status_code=400, detail="缺少动作名称")
                
                # 查找动作
                action = next((a for a in self._actions if a.name == action_name), None)
                if not action:
                    raise HTTPException(status_code=404, detail=f"未找到动作: {action_name}")
                
                # 执行动作
                if action.handler:
                    args = action_data.get("arguments", {})
                    result = await action.handler(**args)
                    return {"result": result}
                else:
                    return {"result": "动作未实现处理函数"}
            
            except Exception as e:
                logger.error(f"❌ [CopilotRuntime] 动作执行失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        logger.info("📝 [CopilotRuntime] API路由注册完成")
    
    async def _stream_chat_response(self, request_data: Dict[str, Any]):
        """流式聊天响应生成器"""
        import json
        
        async for response_chunk in self._resolver.generate_copilot_response(request_data):
            # 将响应转换为JSON字符串
            yield json.dumps(response_chunk, ensure_ascii=False) + "\n"
    
    async def _stream_chat_sse(self, request_data: Dict[str, Any]):
        """SSE格式的流式响应生成器"""
        import json
        
        async for response_chunk in self._resolver.generate_copilot_response(request_data):
            # SSE格式
            sse_data = f"data: {json.dumps(response_chunk, ensure_ascii=False)}\n\n"
            yield sse_data
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
    
    async def process_runtime_request(self, **kwargs) -> Dict[str, Any]:
        """
        处理运行时请求
        
        对标TypeScript的processRuntimeRequest方法
        """
        # 这个方法在TypeScript版本中主要负责设置事件源和处理逻辑
        # 在Python版本中，我们简化为直接返回配置信息
        
        thread_id = kwargs.get("threadId") or f"thread_{id(self)}"
        run_id = kwargs.get("runId") or f"run_{id(self)}"
        
        return {
            "threadId": thread_id,
            "runId": run_id,
            "serviceAdapter": self._service_adapter,
            "actions": self._actions,
            "agentEndpoints": self._agent_endpoints
        }
    
    def start(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """
        启动运行时服务器
        
        Args:
            host: 主机地址
            port: 端口号
            **kwargs: 其他uvicorn参数
        """
        import uvicorn
        
        logger.info(f"🚀 [CopilotRuntime] 启动服务器: {host}:{port}")
        
        # 设置默认服务适配器
        if self._service_adapter is None:
            logger.warning("⚠️ [CopilotRuntime] 未配置服务适配器，使用空适配器")
            self._service_adapter = EmptyAdapter()
        
        # 启动服务器
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            **kwargs
        )


def create_copilot_runtime() -> CopilotRuntime:
    """创建CopilotRuntime实例的工厂函数"""
    return CopilotRuntime() 