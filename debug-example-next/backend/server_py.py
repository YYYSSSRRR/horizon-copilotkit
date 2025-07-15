#!/usr/bin/env python3
"""
CopilotKit Debug Example Next - Backend Server (Python Runtime)
基于 runtime-py 的 FastAPI 后端服务
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

# 添加 runtime-py 到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
runtime_py_path = project_root / "CopilotKit" / "packages" / "runtime-py"
sys.path.insert(0, str(runtime_py_path))

try:
    from copilotkit_runtime import (
        CopilotRuntime,
        Action,
        Parameter,
        MessageRole,
        MessageType
    )
    from copilotkit_runtime.integrations import create_copilot_runtime_server
    from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter
    from copilotkit_runtime.utils import random_id
except ImportError as e:
    print(f"错误: 无法导入 runtime-py 模块: {e}")
    print(f"请确保 runtime-py 路径正确: {runtime_py_path}")
    sys.exit(1)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend.log')
    ]
)

logger = logging.getLogger(__name__)


def create_demo_actions() -> List[Action]:
    """创建演示动作"""
    
    async def get_current_time(arguments: Dict[str, Any]) -> str:
        """获取当前时间"""
        timezone = arguments.get("timezone", "UTC")
        try:
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"⏰ 获取当前时间: {formatted_time} ({timezone})")
            return f"当前时间 ({timezone}): {formatted_time}"
        except Exception as e:
            logger.error(f"获取时间失败: {e}")
            return f"获取时间失败: {str(e)}"
    
    async def calculate(arguments: Dict[str, Any]) -> str:
        """计算数学表达式"""
        expression = arguments.get("expression", "")
        try:
            # 简单的安全计算
            if any(op in expression for op in ['import', 'exec', 'eval', '__', 'open', 'file']):
                return "不安全的表达式，计算被拒绝"
            
            # 只允许基本的数学运算
            allowed_chars = set('0123456789+-*/()., ')
            if not all(c in allowed_chars for c in expression):
                return "包含不允许的字符，只支持基本数学运算"
            
            result = eval(expression)
            logger.info(f"🧮 计算: {expression} = {result}")
            return f"计算结果: {expression} = {result}"
        except ZeroDivisionError:
            return "错误: 除零操作"
        except Exception as e:
            logger.error(f"计算失败: {e}")
            return f"计算错误: {str(e)}"
    
    async def get_user_info(arguments: Dict[str, Any]) -> str:
        """获取用户信息"""
        user_id = arguments.get("user_id", "default")
        try:
            # 模拟用户数据
            users_db = {
                "default": {"name": "演示用户", "role": "guest", "last_login": "2024-01-15"},
                "admin": {"name": "管理员", "role": "admin", "last_login": "2024-01-16"},
                "user1": {"name": "张三", "role": "user", "last_login": "2024-01-14"}
            }
            
            user_info = users_db.get(user_id, {
                "name": "未知用户",
                "role": "guest", 
                "last_login": "从未登录"
            })
            
            result = f"用户信息 - 姓名: {user_info['name']}, 角色: {user_info['role']}, 最后登录: {user_info['last_login']}"
            logger.info(f"👤 获取用户信息: {user_id} -> {user_info}")
            return result
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return f"获取用户信息失败: {str(e)}"
    
    async def check_status(arguments: Dict[str, Any]) -> str:
        """检查系统状态"""
        service = arguments.get("service", "system")
        try:
            # 模拟系统状态检查
            status_db = {
                "system": {"status": "运行中", "uptime": "24小时", "cpu": "45%", "memory": "62%"},
                "database": {"status": "正常", "connections": "8/100", "response_time": "12ms"},
                "api": {"status": "正常", "requests_per_min": "150", "error_rate": "0.1%"},
                "cache": {"status": "正常", "hit_rate": "89%", "memory_usage": "34%"}
            }
            
            service_status = status_db.get(service, {
                "status": "未知服务",
                "message": f"服务 '{service}' 不存在"
            })
            
            if "message" in service_status:
                result = service_status["message"]
            else:
                status_info = ", ".join([f"{k}: {v}" for k, v in service_status.items()])
                result = f"{service.upper()} 状态 - {status_info}"
            
            logger.info(f"📊 检查状态: {service} -> {service_status}")
            return result
        except Exception as e:
            logger.error(f"状态检查失败: {e}")
            return f"状态检查失败: {str(e)}"
    
    # 创建动作列表
    actions = [
        Action(
            name="get_current_time",
            description="获取当前时间，可指定时区",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区，例如: UTC, Asia/Shanghai, America/New_York",
                        "default": "UTC"
                    }
                }
            },
            handler=get_current_time
        ),
        Action(
            name="calculate",
            description="计算数学表达式，支持基本的四则运算",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，例如: 2+3*4, (10-5)/2"
                    }
                },
                "required": ["expression"]
            },
            handler=calculate
        ),
        Action(
            name="get_user_info",
            description="获取用户信息",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID，可选值: default, admin, user1",
                        "default": "default"
                    }
                }
            },
            handler=get_user_info
        ),
        Action(
            name="check_status",
            description="检查系统或服务状态",
            parameters={
                "type": "object", 
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "服务名称，可选值: system, database, api, cache",
                        "default": "system"
                    }
                }
            },
            handler=check_status
        )
    ]
    
    return actions


def create_copilot_runtime_and_adapter():
    """创建CopilotRuntime和适配器"""
    try:
        # 创建运行时
        runtime = CopilotRuntime()
        
        # 获取DeepSeek API密钥
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            logger.warning("⚠️ 未设置DEEPSEEK_API_KEY环境变量")
            raise ValueError("需要设置DEEPSEEK_API_KEY环境变量")
        
        # 创建DeepSeek适配器
        deepseek_adapter = DeepSeekAdapter(
            api_key=deepseek_api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        )
        
        # 注册演示动作
        demo_actions = create_demo_actions()
        for action in demo_actions:
            runtime._actions.append(action)
        
        logger.info(f"✅ 创建CopilotRuntime成功，注册了 {len(demo_actions)} 个动作")
        logger.info(f"🔧 配置DeepSeek适配器: {deepseek_adapter.get_model()}")
        
        return runtime, deepseek_adapter
    
    except Exception as e:
        logger.error(f"❌ 创建CopilotRuntime失败: {e}")
        raise


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    try:
        # 创建运行时和适配器
        runtime, service_adapter = create_copilot_runtime_and_adapter()
        
        # 创建CopilotRuntimeServer
        copilot_server = create_copilot_runtime_server(
            runtime=runtime,
            service_adapter=service_adapter,
            title="CopilotKit Debug Example (Python Runtime)",
            version="0.1.0",
            cors_origins=["*"]  # 开发环境允许所有源
        )
        
        app = copilot_server.app
        
        # 添加自定义路由
        @app.get("/debug/info")
        async def debug_info():
            """调试信息端点"""
            return {
                "runtime": "CopilotKit Python Runtime",
                "version": "0.1.0",
                "adapter": type(service_adapter).__name__,
                "model": service_adapter.get_model(),
                "actions_count": len(runtime.get_actions()),
                "actions": [action.name for action in runtime.get_actions()],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @app.get("/debug/test")
        async def debug_test():
            """调试测试端点"""
            return {
                "message": "CopilotKit Python Runtime 运行正常",
                "test_actions": [
                    "试试问我: '现在几点了？'",
                    "试试问我: '帮我计算 2+3*4'", 
                    "试试问我: '查看系统状态'",
                    "试试问我: '获取用户信息'"
                ]
            }
        
        logger.info("🌐 FastAPI应用创建完成")
        return app
    
    except Exception as e:
        logger.error(f"❌ 创建FastAPI应用失败: {e}")
        raise


# 创建应用实例
app = create_app()

# 主函数
def main():
    """启动服务器"""
    logger.info("🚀 启动CopilotKit Debug Example (Python Runtime)")
    
    port = 8002  # 直接硬编码端口
    host = "0.0.0.0"
    
    print(f"DEBUG: port={port}, host={host}")  # 调试信息
    
    logger.info(f"📡 服务器配置:")
    logger.info(f"   - 地址: {host}:{port}")
    logger.info(f"   - API文档: http://{host}:{port}/docs") 
    logger.info(f"   - 健康检查: http://{host}:{port}/api/health")
    logger.info(f"   - 调试信息: http://{host}:{port}/debug/info")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            reload=False  # 生产环境设为False
        )
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")


if __name__ == "__main__":
    main() 