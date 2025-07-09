#!/usr/bin/env python3
"""
CopilotKit Debug Example Next - Backend Server
基于 copilotkit-runtime-next 的 FastAPI 后端服务
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 添加 CopilotKit runtime-next 到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
runtime_next_path = project_root / "CopilotKit" / "packages" / "runtime-next"
sys.path.insert(0, str(runtime_next_path))

try:
    from copilotkit_runtime import (
        CopilotRuntime,
        OpenAIAdapter, 
        DeepSeekAdapter,
        Action,
        Parameter,
        ParameterType,
        RequestContext,
        CopilotRuntimeRequest,
        Message
    )
    from copilotkit_runtime.integrations import CopilotRuntimeServer
    from copilotkit_runtime.types.messages import convert_json_to_messages, convert_messages_to_json
    from copilotkit_runtime.utils.common import generate_id
except ImportError as e:
    print(f"错误: 无法导入 runtime-next 模块: {e}")
    print(f"请确保 runtime-next 路径正确: {runtime_next_path}")
    sys.exit(1)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 应用配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# 创建 FastAPI 应用
app = FastAPI(
    title="CopilotKit Debug Example Next Backend",
    description="基于 runtime-next 的调试示例后端服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 示例动作定义
def create_demo_actions() -> List[Action]:
    """创建演示动作"""
    actions = []
    
    # 获取当前时间
    async def get_current_time(arguments: Dict[str, Any]) -> str:
        """获取当前时间"""
        timezone = arguments.get("timezone", "Asia/Shanghai")
        current = datetime.now()
        return f"当前时间是: {current.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})"
    
    actions.append(Action(
        name="get_current_time",
        description="获取当前时间",
        parameters=[
            Parameter(
                name="timezone",
                type=ParameterType.STRING,
                description="时区 (默认: Asia/Shanghai)",
                required=False
            )
        ],
        handler=get_current_time
    ))
    
    # 数学计算
    async def calculate(arguments: Dict[str, Any]) -> str:
        """执行数学计算"""
        try:
            expression = arguments.get("expression", "")
            if not expression:
                return "请提供要计算的表达式"
            
            # 简单的安全计算（仅支持基本运算）
            allowed_chars = set("0123456789+-*/(). ")
            if not all(c in allowed_chars for c in expression):
                return "表达式包含不支持的字符"
            
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    actions.append(Action(
        name="calculate",
        description="执行数学计算",
        parameters=[
            Parameter(
                name="expression",
                type=ParameterType.STRING,
                description="数学表达式 (如: 2+3*4)",
                required=True
            )
        ],
        handler=calculate
    ))
    
    # 用户信息查询
    async def get_user_info(arguments: Dict[str, Any]) -> str:
        """获取用户信息"""
        info_type = arguments.get("type", "basic")
        
        if info_type == "basic":
            return "用户: 调试用户\n状态: 在线\n权限: 标准用户"
        elif info_type == "system":
            return f"系统信息:\n- Python版本: {sys.version}\n- 平台: {sys.platform}\n- 工作目录: {os.getcwd()}"
        else:
            return "支持的信息类型: basic, system"
    
    actions.append(Action(
        name="get_user_info",
        description="获取用户或系统信息",
        parameters=[
            Parameter(
                name="type",
                type=ParameterType.STRING,
                description="信息类型: basic(基本信息) 或 system(系统信息)",
                required=False
            )
        ],
        handler=get_user_info
    ))
    
    # 状态检查
    async def check_status(arguments: Dict[str, Any]) -> str:
        """检查系统状态"""
        component = arguments.get("component", "all")
        
        status = {
            "backend": "✅ 运行中",
            "runtime": "✅ 已初始化",
            "actions": f"✅ {len(actions)} 个动作可用",
            "adapters": "✅ OpenAI & DeepSeek 适配器已加载"
        }
        
        if component == "all":
            return "\n".join([f"{k}: {v}" for k, v in status.items()])
        elif component in status:
            return f"{component}: {status[component]}"
        else:
            return f"未知组件: {component}。可用组件: {', '.join(status.keys())}"
    
    actions.append(Action(
        name="check_status",
        description="检查系统状态",
        parameters=[
            Parameter(
                name="component",
                type=ParameterType.STRING,
                description="要检查的组件 (backend, runtime, actions, adapters 或 all)",
                required=False
            )
        ],
        handler=check_status
    ))
    
    return actions

def create_copilot_runtime_and_adapter():
    """创建 CopilotRuntime 实例和适配器"""
    
    # 选择适配器
    adapter = None
    
    # 使用 DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        adapter = DeepSeekAdapter(api_key=deepseek_key, model=model)
        logger.info(f"使用 DeepSeek 适配器, 模型: {model}")
    
    if not adapter:
        raise ValueError("请配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY")
    
    # 创建动作
    actions = create_demo_actions()
    logger.info(f"创建了 {len(actions)} 个示例动作")
    
    # 创建运行时
    runtime = CopilotRuntime(actions=actions)
    
    logger.info("CopilotRuntime 初始化完成")
    return runtime, adapter

# 创建运行时实例
try:
    runtime, service_adapter = create_copilot_runtime_and_adapter()
except Exception as e:
    logger.error(f"创建运行时失败: {e}")
    runtime = None
    service_adapter = None

# 创建 CopilotKit 服务器
if runtime and service_adapter:
    copilot_server = CopilotRuntimeServer(
        runtime=runtime,
        service_adapter=service_adapter,
        title="CopilotKit Debug Example Next Backend",
        version="1.0.0",
        cors_origins=CORS_ORIGINS
    )
    
    # 将 CopilotKit 路由挂载到主应用的 /api/copilotkit 路径
    app.mount("/api/copilotkit", copilot_server.app)
    
    logger.info("CopilotKit 服务器创建完成")
    logger.info("可用端点:")
    logger.info("- POST /api/copilotkit/api/chat - 聊天端点")
    logger.info("- GET /api/copilotkit/api/health - 健康检查")
    logger.info("- GET /api/copilotkit/ - 服务信息")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "copilotkit-debug-example-next",
        "version": "1.0.0",
        "runtime_available": runtime is not None
    }
    
    if runtime and service_adapter:
        status.update({
            "adapter": {
                "provider": service_adapter.get_provider_name(),
                "model": service_adapter.get_model_name()
            },
            "actions_count": len(runtime.actions)
        })
    
    return JSONResponse(content=status)

# 根路径
@app.get("/")
async def root():
    """根路径信息"""
    return {
        "message": "CopilotKit Debug Example Next Backend",
        "description": "基于 runtime-next 的调试示例后端服务",
        "endpoints": {
            "health": "/health",
            "copilotkit": "/api/copilotkit",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    logger.info(f"启动服务器: http://{HOST}:{PORT}")
    logger.info(f"API文档: http://{HOST}:{PORT}/docs")
    logger.info(f"健康检查: http://{HOST}:{PORT}/health")
    
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    ) 