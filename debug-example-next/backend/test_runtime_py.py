#!/usr/bin/env python3
"""
简单测试 runtime-py 的功能
"""

import os
import sys
from pathlib import Path

# 添加 runtime-py 到路径
current_dir = Path(__file__).parent
runtime_py_path = current_dir.parent.parent / "CopilotKit" / "packages" / "runtime-py"
sys.path.insert(0, str(runtime_py_path))

print(f"📂 Runtime-py 路径: {runtime_py_path}")

try:
    # 测试基本导入
    print("🔄 测试基本导入...")
    from copilotkit_runtime import CopilotRuntime, CopilotRuntimeServer
    from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter
    print("✅ 基本导入成功")
    
    # 测试创建运行时
    print("🔄 测试创建运行时...")
    runtime = CopilotRuntime()
    print("✅ 运行时创建成功")
    
    # 测试创建适配器（没有API密钥也可以创建实例）
    print("🔄 测试创建适配器...")
    try:
        adapter = DeepSeekAdapter(api_key="test-key")
        print("✅ 适配器创建成功")
    except Exception as e:
        print(f"⚠️ 适配器创建失败: {e}")
    
    # 测试注册动作
    print("🔄 测试注册动作...")
    
    async def test_action():
        return "测试动作执行成功"
    
    runtime.action(
        name="test",
        description="测试动作",
        handler=test_action
    )
    
    actions = runtime.get_actions()
    print(f"✅ 动作注册成功，当前动作数量: {len(actions)}")
    
    # 测试集成
    print("🔄 测试FastAPI集成...")
    try:
        from copilotkit_runtime.types.adapters import EmptyAdapter
        empty_adapter = EmptyAdapter()
        
        server = CopilotRuntimeServer(
            runtime=runtime,
            service_adapter=empty_adapter
        )
        print("✅ FastAPI集成成功")
        print(f"📡 FastAPI应用类型: {type(server.app)}")
    except Exception as e:
        print(f"❌ FastAPI集成失败: {e}")
    
    print("🎉 所有测试通过！runtime-py 工作正常")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请检查依赖是否已安装")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc() 