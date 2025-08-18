#!/bin/bash

# 分析 coloringbook.ai 网站菜单的快速脚本

echo "🎨 分析 ColoringBook.ai 网站菜单"
echo "================================"

# 检查是否设置了 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  请先设置 DEEPSEEK_API_KEY 环境变量:"
    echo "   export DEEPSEEK_API_KEY=your-deepseek-api-key"
    echo ""
    echo "或者你可以使用以下命令临时设置:"
    echo "   DEEPSEEK_API_KEY=your-deepseek-api-key ./scripts/analyze-coloringbook.sh"
    exit 1
fi

# 确保在正确的目录
cd "$(dirname "$0")/.."

echo "📦 安装依赖..."
npm install --silent

echo "🔍 开始分析..."

# 方法1: 使用编程方式
echo "方法1: 使用编程接口分析"
npx tsx examples/analyze-coloringbook.ts

echo ""
echo "================================"
echo ""

# 方法2: 使用CLI命令
echo "方法2: 使用CLI命令分析"
npx tsx src/cli.ts analyze \
  --url "https://www.coloringbook.ai/zh" \
  --output "./results/coloringbook-cli-analysis" \
  --menu-selectors "nav a,.navbar a,.menu a,.header a" \
  --exclude-patterns "mailto:,tel:,javascript:,#,facebook.com,twitter.com" \
  --max-depth 2 \
  --concurrency 2 \
  --delay 2000 \
  --llm-model "deepseek-chat"

echo ""
echo "✅ 分析完成！"
echo "📁 查看结果文件:"
echo "   - examples/results/coloringbook-analysis.json"
echo "   - results/coloringbook-cli-analysis.json"