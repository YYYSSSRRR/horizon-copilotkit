#!/usr/bin/env python3
"""
审批系统测试脚本
用于测试人工审批工具调用的完整流程
"""

import asyncio
import json
import httpx
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8005"

async def test_approval_system():
    """测试审批系统的完整流程"""
    print("🧪 开始测试审批系统...")
    
    async with httpx.AsyncClient() as client:
        
        # 1. 检查审批系统状态
        print("\n1️⃣ 检查审批系统状态")
        try:
            response = await client.get(f"{BASE_URL}/api/approvals/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ 审批系统状态: {status['status']}")
                print(f"📊 待审批数量: {status['pending_count']}")
            else:
                print(f"❌ 获取状态失败: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("请确保后端服务器正在运行: python backend/server_py.py")
            return
        
        # 2. 查看当前待审批列表
        print("\n2️⃣ 查看当前待审批列表")
        response = await client.get(f"{BASE_URL}/api/approvals/pending")
        pending_data = response.json()
        print(f"📋 当前待审批数量: {pending_data['pending_count']}")
        
        if pending_data['pending_count'] > 0:
            print("待审批请求:")
            for req in pending_data['pending_requests']:
                print(f"  - {req['tool_name']} (ID: {req['approval_id'][:8]}...)")
                print(f"    参数: {req['arguments']}")
                print(f"    时间: {req['timestamp']}")
        
        # 3. 模拟一些待审批请求（如果没有的话）
        if pending_data['pending_count'] == 0:
            print("\n3️⃣ 没有待审批请求，请先与AI聊天机器人对话，让它调用需要审批的工具")
            print("例如：")
            print("  - '帮我计算 2+3*4' (会触发 calculate 工具)")
            print("  - '检查系统状态' (会触发 check_status 工具)")
            print("\n等待新的审批请求...")
            
            # 等待并检查是否有新的审批请求
            for i in range(30):  # 等待30秒
                await asyncio.sleep(1)
                response = await client.get(f"{BASE_URL}/api/approvals/pending")
                new_pending_data = response.json()
                
                if new_pending_data['pending_count'] > 0:
                    print(f"\n✅ 检测到 {new_pending_data['pending_count']} 个新的待审批请求!")
                    pending_data = new_pending_data
                    break
                
                if i % 5 == 0:
                    print(f"⏳ 等待中... ({30-i}秒)")
            
            if pending_data['pending_count'] == 0:
                print("\n⏰ 等待超时，没有检测到新的审批请求")
                return
        
        # 4. 测试审批功能
        if pending_data['pending_count'] > 0:
            print(f"\n4️⃣ 测试审批功能")
            first_request = pending_data['pending_requests'][0]
            approval_id = first_request['approval_id']
            tool_name = first_request['tool_name']
            
            print(f"📝 准备审批工具调用: {tool_name}")
            print(f"🆔 审批ID: {approval_id}")
            print(f"📋 参数: {first_request['arguments']}")
            
            # 询问用户是否批准
            user_choice = input(f"\n❓ 是否批准这个 {tool_name} 工具调用? (y/n): ").lower().strip()
            
            approved = user_choice in ['y', 'yes', 'Y', 'YES', '是', '批准']
            
            # 发送审批请求
            approval_request = {
                "approval_id": approval_id,
                "approved": approved
            }
            
            print(f"\n📤 发送审批决定: {'批准' if approved else '拒绝'}")
            response = await client.post(
                f"{BASE_URL}/api/approvals/approve",
                json=approval_request
            )
            
            if response.status_code == 200:
                approval_result = response.json()
                print(f"✅ 审批处理成功!")
                print(f"📊 状态: {approval_result['status']}")
                
                if approval_result.get('result'):
                    print(f"🎯 执行结果: {approval_result['result']}")
                
                if approval_result.get('error'):
                    print(f"❌ 执行错误: {approval_result['error']}")
            else:
                print(f"❌ 审批处理失败: {response.status_code}")
                print(f"错误信息: {response.text}")
        
        # 5. 再次检查状态
        print("\n5️⃣ 最终状态检查")
        response = await client.get(f"{BASE_URL}/api/approvals/status")
        final_status = response.json()
        print(f"📊 最终待审批数量: {final_status['pending_count']}")
        
        response = await client.get(f"{BASE_URL}/api/approvals/pending")
        final_pending = response.json()
        
        if final_pending['pending_count'] > 0:
            print("剩余待审批请求:")
            for req in final_pending['pending_requests']:
                print(f"  - {req['tool_name']} (ID: {req['approval_id'][:8]}...)")
        else:
            print("✅ 没有剩余的待审批请求")

def print_usage():
    """打印使用说明"""
    print("🔐 CopilotKit 审批系统测试工具")
    print("=" * 50)
    print("此脚本用于测试人工审批工具调用功能")
    print()
    print("使用步骤:")
    print("1. 确保后端服务器正在运行:")
    print("   cd backend && python server_py.py")
    print()
    print("2. 运行此测试脚本:")
    print("   python test_approval_system.py")
    print()
    print("3. 在另一个终端中与AI对话，触发需要审批的工具:")
    print("   - '帮我计算 2+3*4'")
    print("   - '检查系统状态'")
    print()
    print("4. 返回到此脚本查看和处理审批请求")
    print()

async def main():
    """主函数"""
    print_usage()
    input("按 Enter 键开始测试...")
    await test_approval_system()
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(main())