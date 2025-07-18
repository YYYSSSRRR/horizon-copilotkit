#!/bin/bash

# CopilotKit + DeepSeek Debug 模式启动脚本
echo "🐛 启动 CopilotKit + DeepSeek 调试模式"
echo "======================================"

# 检查环境变量
if [ ! -f "backend/.env" ]; then
    echo "⚠️  警告: 未找到 backend/.env 文件"
    echo "📝 请先配置环境变量:"
    echo "   cd backend && cp env.example .env"
    exit 1
fi

echo "🔧 调试模式特性:"
echo "   - 后端启用调试端口 9229"
echo "   - 可在 VS Code 中附加调试器"
echo "   - 支持断点和代码跟踪"
echo ""

# 使用 concurrently 同时启动前后端
if command -v concurrently &> /dev/null; then
    echo "🚀 正在启动调试模式..."
    concurrently \
        --names "BACKEND-DEBUG,FRONTEND" \
        --prefix-colors "red,green" \
        "cd backend && npm run dev:debug" \
        "cd frontend && npm run dev"
else
    echo "⚠️  未找到 concurrently，请手动启动:"
    echo "   终端1: cd backend && npm run dev:debug"
    echo "   终端2: cd frontend && npm run dev"
    echo ""
    echo "📍 调试器连接:"
    echo "   在 VS Code 中按 F5，选择 '🔧 Debug Backend (Attach)'"
fi 