#!/usr/bin/env python3
"""
CopilotKit Runtime Next CLI

命令行工具，用于启动CopilotKit Runtime服务器。
"""

import argparse
import os
import sys
import logging
from typing import Optional

from .runtime import CopilotRuntime
from .adapters import OpenAIAdapter, DeepSeekAdapter
from .integrations import CopilotRuntimeServer


def setup_logging(level: str = "info") -> None:
    """设置日志级别"""
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    log_level = level_map.get(level.lower(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def create_adapter(provider: str, api_key: Optional[str] = None, model: Optional[str] = None) -> any:
    """创建适配器"""
    api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未提供API密钥。请通过--api-key参数或环境变量提供。")
        sys.exit(1)
    
    if provider.lower() == "deepseek":
        return DeepSeekAdapter(
            api_key=api_key,
            model=model or "deepseek-chat",
        )
    else:
        return OpenAIAdapter(
            api_key=api_key,
            model=model or "gpt-4",
        )


def main() -> None:
    """CLI主函数"""
    parser = argparse.ArgumentParser(
        description="CopilotKit Runtime Next - Python运行时服务器"
    )
    
    # 基本参数
    parser.add_argument("--host", default="0.0.0.0", help="监听主机 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], 
                        help="日志级别 (默认: info)")
    
    # 适配器配置
    parser.add_argument("--provider", default="openai", choices=["openai", "deepseek"], 
                        help="LLM提供商 (默认: openai)")
    parser.add_argument("--api-key", help="API密钥 (也可通过环境变量设置)")
    parser.add_argument("--model", help="模型名称 (默认根据提供商选择)")
    
    # CORS配置
    parser.add_argument("--cors-origins", nargs="*", default=["*"], 
                        help="CORS允许的源 (默认: *)")
    
    # 服务器配置
    parser.add_argument("--title", default="CopilotKit Runtime Next", 
                        help="API标题 (默认: CopilotKit Runtime Next)")
    parser.add_argument("--reload", action="store_true", help="启用自动重载")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    # 创建适配器
    adapter = create_adapter(args.provider, args.api_key, args.model)
    
    # 创建运行时
    runtime = CopilotRuntime()
    
    # 创建服务器
    server = CopilotRuntimeServer(
        runtime=runtime,
        service_adapter=adapter,
        title=args.title,
        cors_origins=args.cors_origins,
    )
    
    # 打印启动信息
    print(f"\n🚀 启动 CopilotKit Runtime Next 服务器")
    print(f"=" * 50)
    print(f"📡 监听地址: http://{args.host}:{args.port}")
    print(f"🔌 使用适配器: {adapter}")
    print(f"🌐 CORS配置: {args.cors_origins}")
    print(f"📚 API文档: http://{args.host}:{args.port}/docs")
    print(f"=" * 50)
    
    # 启动服务器
    server.run(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main() 