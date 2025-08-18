# 快速开始 - 分析 ColoringBook.ai

## 🎯 分析 https://www.coloringbook.ai/zh 的菜单

### 方法1: 使用命令行（推荐）

```bash
# 1. 进入项目目录
cd CopilotKit/packages/menu-analysis

# 2. 设置 DeepSeek API Key  
export DEEPSEEK_API_KEY=your-deepseek-api-key

# 3. 快速分析
./scripts/analyze-coloringbook.sh
```

### 方法2: 直接使用 CLI 命令

```bash
# 进入目录
cd CopilotKit/packages/menu-analysis

# 安装依赖
npm install

# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY=your-deepseek-api-key

# 分析命令
npx tsx src/cli.ts analyze \
  --url "https://www.coloringbook.ai/zh" \
  --output "./results/coloringbook-analysis" \
  --menu-selectors "nav a,.navbar a,.menu a,.header a,.btn[href]" \
  --exclude-patterns "mailto:,tel:,javascript:,#,facebook.com,twitter.com,privacy,terms" \
  --max-depth 2 \
  --concurrency 2 \
  --delay 2000
```

### 方法3: 编程方式

```bash
# 运行预配置的分析脚本
cd CopilotKit/packages/menu-analysis
export DEEPSEEK_API_KEY=your-deepseek-api-key
npx tsx examples/analyze-coloringbook.ts
```

## 🔧 针对 ColoringBook.ai 的特殊配置

### 菜单选择器
专门为 AI 工具网站优化的选择器：
```javascript
[
  'nav a',              // 主导航
  '.navbar a',          // 导航栏
  '.menu a',            // 菜单
  '.header a',          // 头部链接
  '.btn[href]',         // 按钮链接
  '.tool-nav a',        // 工具导航
  '.feature-nav a',     // 功能导航
  '.product-nav a'      // 产品导航
]
```

### 排除模式
避免分析不相关的链接：
```javascript
[
  'mailto:', 'tel:', 'javascript:', '#',
  'facebook.com', 'twitter.com', 'instagram.com',
  'privacy', 'terms', 'contact', 'about-us'
]
```

## 📊 预期分析结果

ColoringBook.ai 的菜单分析可能包含：

1. **主要功能菜单**
   - AI 着色书生成
   - 模板库浏览
   - 用户作品展示

2. **工具相关菜单**
   - 创建新项目
   - 编辑工具
   - 分享功能

3. **用户功能**
   - 登录/注册
   - 个人中心
   - 订阅/付费

## 🎯 单页面快速分析

如果只想分析主页：

```bash
npx tsx src/cli.ts single \
  --url "https://www.coloringbook.ai/zh" \
  --name "ColoringBook AI 主页" \
  --output "./results/homepage-analysis.json"
```

## 📁 查看结果

分析完成后，查看结果文件：
- `results/coloringbook-analysis.json` - 完整分析结果（JSON格式）
- `results/homepage-analysis.json` - 单页分析结果（JSON格式）

JSON结果包含：
- 菜单名称和URL
- 主要功能描述
- 用户可执行操作
- 业务范围和使用场景
- 置信度评分
- 详细的元数据和时间戳

## 🚨 注意事项

1. **API Key**: 确保设置有效的 OpenAI API Key
2. **访问频率**: 设置了2秒延迟，避免对网站造成压力
3. **网络环境**: 确保能正常访问目标网站
4. **中文分析**: 专门配置了中文提示词，输出中文分析结果

## 🛠️ 故障排除

### 常见问题

1. **API Key 错误**
   ```bash
   export DEEPSEEK_API_KEY=sk-your-actual-deepseek-api-key
   ```

2. **网络超时**
   - 检查网络连接
   - 增加 timeout 设置

3. **找不到菜单**
   - 网站结构可能有变化
   - 调整菜单选择器

4. **依赖安装失败**
   ```bash
   npm install --legacy-peer-deps
   ```

### 调试模式

启用详细日志：
```bash
npx tsx src/cli.ts analyze \
  --url "https://www.coloringbook.ai/zh" \
  --verbose
```

查看日志文件：
- `menu-analysis.log` - 详细日志
- `progress.json` - 进度状态