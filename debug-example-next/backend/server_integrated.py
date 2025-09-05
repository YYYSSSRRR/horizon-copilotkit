#!/usr/bin/env python3
"""
使用新的集成审批系统的服务器
基于 CopilotKit runtime-python 的审批功能
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# 导入 CopilotKit 组件
# 添加 runtime-python 到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
runtime_python_path = project_root / "CopilotKit" / "packages" / "runtime-python"
sys.path.insert(0, str(runtime_python_path))
try:
    from copilotkit_runtime import (
        CopilotRuntime,
        CopilotRuntimeConstructorParams,
        DeepSeekAdapter,
        create_copilot_app,
        Action,
        Parameter
    )
except ImportError as e:
    print(f"错误: 无法导入 runtime-python 模块: {e}")
    print(f"请确保 runtime-python 路径正确: {runtime_python_path}")
    sys.exit(1)


# ================================
# 工具函数定义
# ================================

async def get_current_time(arguments: Dict[str, Any]) -> str:
    """获取当前时间"""
    timezone_str = arguments.get('timezone', 'UTC')
    
    logger.info("获取当前时间", timezone=timezone_str)
    
    try:
        if timezone_str == 'Asia/Shanghai':
            from datetime import timezone, timedelta
            tz = timezone(timedelta(hours=8))
        elif timezone_str == 'America/New_York':
            from datetime import timezone, timedelta
            tz = timezone(timedelta(hours=-5))  # EST
        else:
            tz = timezone.utc
        
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        logger.info("时间获取成功", time=formatted_time)
        return f"当前时间 ({timezone_str}): {formatted_time}"
        
    except Exception as e:
        logger.error("获取时间失败", error=str(e))
        return f"获取时间失败: {str(e)}"


async def calculate(arguments: Dict[str, Any]) -> str:
    """计算数学表达式（需要审批）"""
    expression = arguments.get('expression', '')
    
    logger.info("计算数学表达式", expression=expression)
    
    try:
        # 简单的安全检查
        allowed_chars = set('0123456789+-*/()%. ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("表达式包含不允许的字符")
        
        # 计算表达式
        result = eval(expression)  # 注意：实际使用中应该用更安全的方法
        
        logger.info("计算成功", expression=expression, result=result)
        return f"计算结果: {expression} = {result}"
        
    except Exception as e:
        logger.error("计算失败", expression=expression, error=str(e))
        return f"计算失败: {str(e)}"


async def get_user_info(arguments: Dict[str, Any]) -> str:
    """获取用户信息"""
    user_id = arguments.get('user_id', 'default')
    
    logger.info("获取用户信息", user_id=user_id)
    
    users = {
        'default': {
            'name': '默认用户',
            'role': '访客',
            'status': '在线',
            'last_active': '刚刚'
        },
        'admin': {
            'name': '管理员',
            'role': '系统管理员',
            'status': '在线',
            'last_active': '5分钟前'
        },
        'user1': {
            'name': '张三',
            'role': '普通用户',
            'status': '离线',
            'last_active': '1小时前'
        }
    }
    
    user = users.get(user_id, users['default'])
    
    result = f"用户信息:\n- 姓名: {user['name']}\n- 角色: {user['role']}\n- 状态: {user['status']}\n- 最后活跃: {user['last_active']}"
    
    logger.info("用户信息获取成功", user_id=user_id, user=user)
    return result


async def check_status(arguments: Dict[str, Any]) -> str:
    """检查系统状态（需要审批）"""
    service = arguments.get('service', 'system')
    
    logger.info("检查系统状态", service=service)
    
    status_map = {
        'system': {
            'name': '系统',
            'status': '运行中',
            'uptime': '24小时15分钟',
            'cpu': '15%',
            'memory': '45%'
        },
        'database': {
            'name': '数据库',
            'status': '正常',
            'connections': '12/100',
            'response_time': '2ms'
        },
        'api': {
            'name': 'API服务',
            'status': '健康',
            'requests_per_minute': '150',
            'error_rate': '0.1%'
        },
        'cache': {
            'name': '缓存服务',
            'status': '正常',
            'hit_rate': '95%',
            'memory_usage': '60%'
        }
    }
    
    info = status_map.get(service, status_map['system'])
    
    result = f"{info['name']}状态:\n"
    for key, value in info.items():
        if key != 'name':
            result += f"- {key.replace('_', ' ').title()}: {value}\n"
    
    logger.info("状态检查完成", service=service, status=info)
    return result.strip()


# ================================
# 主服务器设置
# ================================

def create_demo_actions():
    """创建演示动作列表"""
    actions = [
        # 无需审批的工具
        Action(
            name="get_current_time",
            description="获取当前时间，可指定时区（无需审批）",
            parameters=[
                Parameter(
                    name="timezone",
                    type="string",
                    description="时区，例如: UTC, Asia/Shanghai, America/New_York",
                    required=False
                )
            ],
            handler=get_current_time
        ),
        Action(
            name="get_user_info",
            description="获取用户信息（无需审批）",
            parameters=[
                Parameter(
                    name="user_id",
                    type="string",
                    description="用户ID，可选值: default, admin, user1",
                    required=False
                )
            ],
            handler=get_user_info
        ),
        
        # 需要审批的工具（会被自动包装）
        Action(
            name="calculate",
            description="计算数学表达式，支持基本的四则运算",
            parameters=[
                Parameter(
                    name="expression",
                    type="string",
                    description="要计算的数学表达式，例如: 2+3*4, (10-5)/2",
                    required=True
                )
            ],
            handler=calculate
        ),
        Action(
            name="check_status",
            description="检查系统或服务状态",
            parameters=[
                Parameter(
                    name="service",
                    type="string",
                    description="服务名称，可选值: system, database, api, cache",
                    required=False
                )
            ],
            handler=check_status
        )
    ]
    
    logger.info("创建了动作列表", 
                total_actions=len(actions),
                action_names=[action.name for action in actions])
    
    return actions


def main():
    """主函数"""
    logger.info("🚀 启动带审批系统的 CopilotKit 服务器")
    
    # 创建动作
    demo_actions = create_demo_actions()
    
    # 创建 DeepSeek 适配器
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key or deepseek_api_key == "test_key":
        logger.warning("⚠️ 未设置有效的DEEPSEEK_API_KEY环境变量")
        # 可以继续运行，但聊天功能将不可用
        deepseek_api_key = "test_key"
    
    # 创建DeepSeek适配器
    deepseek_adapter = DeepSeekAdapter(
        api_key=deepseek_api_key,
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    )
    
    logger.info("DeepSeek 适配器已创建", model="deepseek-chat")
    
    # 创建带审批系统的 CopilotRuntime
    runtime_params = CopilotRuntimeConstructorParams(
        actions=demo_actions,
        # 启用审批系统
        enable_approval_system=True,
        approval_required_actions=["calculate", "check_status"]  # 指定需要审批的工具
    )
    
    copilot_runtime = CopilotRuntime(runtime_params)
    
    logger.info("CopilotRuntime 已创建", 
                actions_count=len(demo_actions),
                approval_enabled=True,
                approval_required_actions=["calculate", "check_status"])
    
    # 创建 FastAPI 应用
    app = create_copilot_app(
        runtime=copilot_runtime,
        service_adapter=deepseek_adapter,
        prefix="/api/copilotkit",
        title="CopilotKit Runtime with Human-in-the-Loop Approval",
        version="1.0.0-approval",
        cors_origins=["*"]
    )
    
    logger.info("FastAPI 应用已创建")
    
    # 运行服务器
    import uvicorn
    
    host = "127.0.0.1"
    port = 8005
    
    logger.info("🎯 服务器配置:")
    logger.info(f"   - 地址: {host}:{port}")
    logger.info(f"   - API文档: http://{host}:{port}/docs")
    logger.info(f"   - 健康检查: http://{host}:{port}/api/copilotkit/api/health")
    logger.info(f"   - 聊天端点: http://{host}:{port}/api/copilotkit/api/chat/stream")
    logger.info(f"🔐 审批系统端点:")
    logger.info(f"   - 待审批列表: http://{host}:{port}/api/copilotkit/api/approvals/pending")
    logger.info(f"   - 审批工具调用: POST http://{host}:{port}/api/copilotkit/api/approvals/approve")
    logger.info(f"   - 审批系统状态: http://{host}:{port}/api/copilotkit/api/approvals/status")
    
    logger.info("🎉 服务器启动中...")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error("服务器启动失败", error=str(e))
        raise


if __name__ == "__main__":
    main()