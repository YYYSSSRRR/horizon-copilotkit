#!/bin/bash

# CopilotKit + DeepSeek Debug Example 启动脚本
echo "🚀 启动 CopilotKit + DeepSeek + Vite 调试示例"
echo "==========================================="

# 检查环境变量
if [ ! -f "backend/.env" ]; then
    echo "⚠️  警告: 未找到 backend/.env 文件"
    echo "📝 请先复制并配置环境变量:"
    echo "   cd backend && cp env.example .env"
    echo "   然后编辑 .env 文件，添加您的 DEEPSEEK_API_KEY"
    exit 1
fi

# 检查 DeepSeek API Key
if ! grep -q "DEEPSEEK_API_KEY=sk-" backend/.env; then
    echo "⚠️  警告: 请在 backend/.env 中设置有效的 DEEPSEEK_API_KEY"
    echo "🔑 获取 API Key: https://platform.deepseek.com/"
    exit 1
fi

echo "✅ 环境配置检查完成"
echo ""

# 安装依赖
echo "📦 安装依赖..."
if [ ! -d "backend/node_modules" ]; then
    echo "   安装后端依赖..."
    cd backend && npm install && cd ..
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "   安装前端依赖..."
    cd frontend && npm install && cd ..
fi

echo "✅ 依赖安装完成"
echo ""

# 启动服务
echo "🌟 启动服务..."
echo "📍 后端: http://localhost:3001"
echo "📍 前端: http://localhost:3000"
echo "📍 健康检查: http://localhost:3001/health"
echo "📍 可用 Actions: http://localhost:3001/api/actions"
echo ""
echo "🔧 调试提示:"
echo "   - 在 VS Code 中按 F5 启动调试器"
echo "   - 在 CopilotKit/packages/runtime 中设置断点"
echo "   - 查看控制台日志获取详细信息"
echo "   - Vite 提供极快的热重载体验"
echo ""
echo "🚀 正在启动..."

# 使用 concurrently 同时启动前后端
if command -v concurrently &> /dev/null; then
    concurrently \
        --names "BACKEND,FRONTEND" \
        --prefix-colors "blue,green" \
        "cd backend && npm run dev" \
        "cd frontend && npm run dev"
else
    echo "⚠️  未找到 concurrently，请手动启动:"
    echo "   终端1: cd backend && npm run dev"
    echo "   终端2: cd frontend && npm run dev"
    echo ""
    echo "🔧 调试模式 (带断点支持):"
    echo "   终端1: cd backend && npm run dev:debug"
    echo "   终端2: cd frontend && npm run dev"
    echo "   然后在 VS Code 中选择 '🔧 Debug Backend (Attach)' 附加调试器"
fi 