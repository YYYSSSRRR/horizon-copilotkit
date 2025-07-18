# CopilotKit + DeepSeek 流式响应问题诊断指南

## 🔍 问题症状
- 第一次问问题：调用到 debugActions，但前台不返回答复，只显示 "..."
- 第二次问同样问题：前台有答复但不会调用到 debugActions

## 🔧 已实施的修复

### 1. 后端修复
✅ **禁用并行工具调用**
```typescript
const serviceAdapter = new DeepSeekAdapter({
  apiKey: process.env.DEEPSEEK_API_KEY!,
  model: "deepseek-chat",
  disableParallelToolCalls: true, // 🔧 关键修复
});
```

✅ **添加详细日志记录**
- HTTP 请求日志
- Action 调用开始/结束日志  
- 错误处理和超时监控

### 2. 前端修复
✅ **启用开发者控制台**
```typescript
<CopilotKit 
  runtimeUrl={`${backendUrl}/api/copilotkit`}
  publicApiKey=""
  showDevConsole={true} // 🔧 启用调试
>
```

✅ **避免缓存问题**
```typescript
const timestamp = new Date().toLocaleTimeString();
const testMessage = new TextMessage({
  content: `现在几点了？(${timestamp})`, // 🔧 添加时间戳
  role: Role.User,
});
```

✅ **添加AI指导指令**
```typescript
<CopilotSidebar
  instructions="你是一个专业的调试助手。当用户询问时间、计算、用户信息或运行时状态时，请务必使用对应的 Action 函数来获取准确信息。不要猜测答案，而是调用相应的函数。"
/>
```

✅ **改进加载状态监控**
- 15秒超时警告
- 停止生成按钮
- 实时调试日志

## 📊 诊断步骤

### 步骤 1: 检查后端启动
```bash
cd debug-example/backend
npm run dev
```

**期望输出:**
```
🎯 CopilotKit Debug Backend 启动成功！
📡 服务器运行在: http://localhost:3001
🔑 API Key 状态: ✅ 已配置
🎯 可用的 Actions: 4
   1. getCurrentTime - 获取当前时间
   2. calculateMath - 执行数学计算
   3. getUserInfo - 获取用户信息
   4. debugRuntimeStatus - 获取运行时调试信息
```

### 步骤 2: 检查前端启动
```bash
cd debug-example/frontend  
npm run dev
```

**期望输出:**
```
Local:   http://localhost:3000/
🔗 Frontend URL: http://localhost:3000
🔗 Backend URL: http://localhost:3001
```

### 步骤 3: 测试健康检查
```bash
curl http://localhost:3001/health
```

**期望响应:**
```json
{
  "status": "ok",
  "deepseek": "configured",
  "actions": [
    {"name": "getCurrentTime", "description": "获取当前时间", "parameters": 0},
    {"name": "calculateMath", "description": "执行数学计算", "parameters": 1},
    {"name": "getUserInfo", "description": "获取用户信息", "parameters": 1},
    {"name": "debugRuntimeStatus", "description": "获取运行时调试信息", "parameters": 0}
  ]
}
```

### 步骤 4: 测试流式响应
在前端界面测试以下消息，观察日志：

#### 测试 1: 时间查询
**发送:** "现在几点了？"

**期望后端日志:**
```
📡 2024-01-XX - POST /api/copilotkit
🔗 CopilotKit 请求: {...}
🔄 [DeepSeek] Processing request: {...}
📤 [DeepSeek] Sending request to API: {...}
🕐 getCurrentTime Action 被调用
🕐 getCurrentTime 返回结果: 当前时间是：...
```

**期望前端日志:**
```
[14:30:22] Messages updated: 2 total, isLoading: false
[14:30:22] Last message: role=assistant, content length=25
[14:30:22] Content preview: "当前时间是：2024-01-XX 14:30:22"
```

#### 测试 2: 数学计算  
**发送:** "计算 10 + 20 * 3"

**期望后端日志:**
```
🧮 calculateMath Action 被调用，参数: {expression: "10 + 20 * 3"}
🧮 calculateMath 返回结果: 计算结果：10 + 20 * 3 = 70
```

### 步骤 5: 检查问题指标

#### 🚨 问题指标 1: 长时间加载
如果看到前端日志：
```
[14:30:37] ⚠️ 检测到长时间加载状态，可能存在流式响应问题
```

**诊断:**
- 检查 DeepSeek API 连接
- 查看后端是否有异常日志
- 验证 API Key 是否有效

#### 🚨 问题指标 2: Action 不被调用
如果后端没有显示 Action 调用日志：

**可能原因:**
- AI 模型没有理解需要调用工具
- 工具定义有问题
- 指导指令不明确

**解决方案:**
- 使用更明确的提示词
- 检查 Action 定义
- 验证 `instructions` 配置

#### 🚨 问题指标 3: 缓存问题
如果第二次问题不调用 Action：

**解决方案:**
- 添加时间戳到消息中
- 清除浏览器缓存
- 使用不同的提问方式

## 🔧 高级诊断

### 查看网络请求
1. 打开浏览器开发者工具
2. 切换到 Network 标签
3. 发送消息
4. 查看 `/api/copilotkit` 请求
5. 检查响应状态和流式数据

### 查看 CopilotKit 内部日志
1. 打开浏览器控制台
2. 查找 `[CopilotKit]` 前缀的日志
3. 注意错误和警告信息

### 检查 DeepSeek API 状态
```bash
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.deepseek.com/v1/models
```

## 📋 常见解决方案

### 解决方案 1: API 配置问题
```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY

# 重新设置
export DEEPSEEK_API_KEY=sk-your-key-here
```

### 解决方案 2: 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :3001
netstat -tulpn | grep :3000

# 终止进程
pkill -f "node.*3001"
pkill -f "node.*3000"
```

### 解决方案 3: 依赖问题
```bash
# 重新安装依赖
cd debug-example/backend && rm -rf node_modules && npm install
cd debug-example/frontend && rm -rf node_modules && npm install
```

### 解决方案 4: 清除缓存
```bash
# 清除 npm 缓存
npm cache clean --force

# 清除浏览器缓存 (Ctrl+Shift+R)
```

## ✅ 成功标志

问题修复成功后，应该看到：

1. **第一次问问题**: ✅ 正常调用 Action 并返回答复
2. **重复问问题**: ✅ 仍然调用 Action（通过时间戳避免缓存）
3. **前端不再显示**: ✅ 持续的 "..." 状态
4. **后端日志清晰**: ✅ 显示完整的请求-响应流程
5. **加载状态正常**: ✅ 不超过 15 秒警告阈值

如果仍有问题，请提供：
- 完整的后端控制台日志
- 前端调试面板的日志
- 浏览器网络请求的详细信息
- 错误消息的截图 