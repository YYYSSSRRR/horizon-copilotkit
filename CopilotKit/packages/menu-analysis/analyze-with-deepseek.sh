#!/bin/bash

# 使用 DeepSeek 分析 ColoringBook.ai 的快速脚本

echo "🤖 使用 DeepSeek 分析 ColoringBook.ai"
echo "==================================="

# 检查 DeepSeek API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  请先设置 DEEPSEEK_API_KEY 环境变量"
    echo ""
    echo "获取 DeepSeek API Key："
    echo "1. 访问 https://platform.deepseek.com/"
    echo "2. 注册账号并获取 API Key"
    echo "3. 设置环境变量："
    echo "   export DEEPSEEK_API_KEY=sk-your-deepseek-api-key"
    echo ""
    exit 1
fi

echo "📋 配置信息："
echo "  - LLM 提供商: DeepSeek"
echo "  - 模型: deepseek-chat"
echo "  - 目标网站: https://www.coloringbook.ai/zh"
echo "  - 并发数: 2"
echo "  - 延迟: 2000ms"
echo ""

# 安装依赖
echo "📦 安装依赖..."
npm install --silent

# 使用 DeepSeek 运行分析
echo "🔍 开始分析..."
npx tsx src/cli.ts analyze \
  --url "https://www.coloringbook.ai/zh" \
  --output "./results/coloringbook-deepseek-analysis" \
  --menu-selectors "nav a,.navbar a,.menu a,.header a,.btn[href],.tool-nav a" \
  --exclude-patterns "mailto:,tel:,javascript:,#,facebook.com,twitter.com,privacy,terms" \
  --max-depth 2 \
  --concurrency 2 \
  --delay 2000 \
  --llm-model "deepseek-chat"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 分析完成！"
    echo ""
    echo "📁 结果文件："
    echo "  - JSON: ./results/coloringbook-deepseek-analysis.json"
    echo ""
    echo "💡 结果以 JSON 格式保存，包含详细的功能分析："
    echo ""
    echo "🔧 调整参数："
    echo "  - 增加并发: --concurrency 3"
    echo "  - 减少延迟: --delay 1000"
    echo "  - 更深层级: --max-depth 3"
else
    echo ""
    echo "❌ 分析失败"
    echo ""
    echo "🛠️ 故障排除："
    echo "1. 检查网络连接"
    echo "2. 验证 DEEPSEEK_API_KEY 是否正确"
    echo "3. 查看详细日志: menu-analysis.log"
    echo "4. 尝试单页分析："
    echo "   npx tsx src/cli.ts single -u https://www.coloringbook.ai/zh -n 'ColoringBook首页'"
fi