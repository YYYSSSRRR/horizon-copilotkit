# CopilotKit Debug Example (DeepSeek + Vite)

这是一个完整的 CopilotKit + DeepSeek 调试示例，包含 Express 后端和 Vite 前端，可以直接调试 `CopilotKit\packages\runtime` 代码。

## 🎯 项目特性

- ✅ **DeepSeek 集成**: 使用 DeepSeek Chat 模型作为 AI 后端
- ✅ **Express 后端**: 使用 CopilotKit Runtime 和自定义 Actions
- ✅ **Vite 前端**: ⚡ 极速开发体验，集成 CopilotKit React 组件
- ✅ **本地包引用**: 直接引用 CopilotKit 源码包进行调试
- ✅ **VS Code 调试**: 完整的调试配置
- ✅ **实时监控**: 后端状态和 Actions 监控
- ✅ **详细日志**: 完整的请求/响应日志
- ✅ **快速热重载**: Vite 提供毫秒级别的 HMR

## 📁 项目结构

```
debug-example/
├── backend/                    # Express 后端
│   ├── src/
│   │   └── server.ts          # 主服务器文件
│   ├── package.json           # 后端依赖
│   ├── tsconfig.json          # TypeScript 配置
│   └── env.example            # 环境变量示例
├── frontend/                   # Vite + React 前端
│   ├── src/
│   │   ├── components/
│   │   │   └── HomePage.tsx   # 主页面组件
│   │   ├── App.tsx            # 根应用组件
│   │   ├── main.tsx           # 应用入口
│   │   ├── index.css          # 全局样式
│   │   └── vite-env.d.ts      # Vite 类型定义
│   ├── index.html             # HTML 入口
│   ├── package.json           # 前端依赖
│   ├── tsconfig.json          # TypeScript 配置
│   ├── vite.config.ts         # Vite 配置
│   ├── tailwind.config.js     # Tailwind 配置
│   └── env.example            # 环境变量示例
├── .vscode/
│   └── launch.json            # VS Code 调试配置
└── README.md                  # 项目说明
```

## 🚀 快速开始

### 1. 环境准备

确保您有以下环境：
- Node.js 18+
- npm 或 yarn
- VS Code (推荐用于调试)
- DeepSeek API Key (从 https://platform.deepseek.com/ 获取)

### 2. 安装依赖

```bash
# 安装后端依赖
cd debug-example/backend
npm install

# 安装前端依赖
cd ../frontend
npm install
```

### 3. 配置环境变量

```bash
# 复制环境变量文件
cd ../backend
cp env.example .env

# 编辑 .env 文件，添加您的 DeepSeek API Key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
```

### 4. 启动开发服务器

```bash
# 启动后端 (终端1)
cd backend
npm run dev

# 启动前端 (终端2)  
cd ../frontend
npm run dev
```

### 5. 访问应用

- 前端界面: http://localhost:3000
- 后端健康检查: http://localhost:3001/health
- 可用 Actions: http://localhost:3001/api/actions

## 🐛 调试指南

### VS Code 调试设置

1. 在 VS Code 中打开 `debug-example` 文件夹
2. 按 `F5` 或使用调试面板
3. 选择以下调试配置之一：
   - `🚀 Debug Backend Server`: 调试后端服务器
   - `🔧 Debug Backend (Attach)`: 附加到运行中的后端
   - `🐛 Debug CopilotKit Runtime`: 专门调试 Runtime 代码

### 设置断点位置

#### 后端断点位置
```typescript
// debug-example/backend/src/server.ts
const runtime = new CopilotRuntime({
  actions: debugActions,
  middleware: {
    onBeforeRequest: async (options) => {
      // 🔴 在这里设置断点，调试请求前处理
      console.log('Request started:', options);
    }
  }
});
```

#### Runtime 核心断点位置
```typescript
// CopilotKit/packages/runtime/src/lib/runtime/copilot-runtime.ts
async processRuntimeRequest(request: CopilotRuntimeRequest): Promise<CopilotRuntimeResponse> {
  // 🔴 在这里设置断点，调试核心请求处理
  const eventSource = new RuntimeEventSource();
  
  // 🔴 在这里设置断点，调试 Actions 获取
  const serverSideActions = await this.getServerSideActions(request);
  
  // 🔴 在这里设置断点，调试消息处理
  const inputMessages = convertGqlInputToMessages(messagesWithInjectedInstructions);
}
```

### 调试步骤

1. **启动调试模式**:
   ```bash
   cd backend
   npm run debug
   ```

2. **在 VS Code 中连接调试器**:
   - 按 `F5`
   - 选择 `🔧 Debug Backend (Attach)`

3. **设置断点**:
   - 在 `server.ts` 中设置断点
   - 在 `CopilotKit/packages/runtime/src/lib/runtime/copilot-runtime.ts` 中设置断点

4. **触发断点**:
   - 在前端界面发送消息
   - 或调用任何 Action

## 🛠️ 可用 Actions

项目包含以下自定义 Actions 用于测试：

### 后端 Actions

1. **`getCurrentTime`** - 获取当前时间
   ```
   "现在几点了？"
   "给我一个 ISO 格式的时间"
   ```

2. **`calculateMath`** - 数学计算
   ```
   "计算 2 + 3 * 4"
   "帮我算一下 (10 + 5) / 3"
   ```

3. **`getUserInfo`** - 查询用户信息
   ```
   "查询用户ID为1的信息"
   "获取用户2的详细信息"
   ```

4. **`debugRuntimeStatus`** - 运行时状态
   ```
   "获取运行时调试状态"
   "显示服务器信息"
   ```

### 前端 Actions

1. **`showNotification`** - 显示通知
   ```
   "显示一个成功通知"
   "弹出一个错误提示"
   ```

## 📊 调试面板功能

前端包含一个调试面板，显示：

- **后端健康状态**: 连接状态、内存使用、运行时间等
- **可用 Actions**: 所有注册的 Actions 列表
- **实时状态监控**: 每30秒更新一次状态

## 🔧 高级调试技巧

### 1. 日志级别控制

设置环境变量来控制日志详细程度：
```bash
DEBUG=copilotkit:* npm run dev
```

### 2. 监控网络请求

在浏览器开发者工具中：
- Network 标签查看 GraphQL 请求
- Console 标签查看前端日志

### 3. Runtime 源码修改

由于项目直接引用 Runtime 源码：
- 可以直接修改 `CopilotKit/packages/runtime` 中的代码
- 修改会立即反映在调试会话中
- 适合深度调试和功能开发

## 🚨 常见问题

### 问题1: 后端启动失败
**解决方案**: 检查 `.env` 文件是否包含有效的 `DEEPSEEK_API_KEY`

### 问题2: 前端无法连接后端
**解决方案**: 确认后端在 3001 端口运行，检查 CORS 配置

### 问题3: 断点不触发
**解决方案**: 
- 确认使用调试模式启动 (`npm run debug`)
- 检查 VS Code 调试配置中的路径设置
- 确认 TypeScript 源映射开启

### 问题4: Actions 不执行
**解决方案**:
- 检查后端日志中的 Action 注册信息
- 确认 DeepSeek API Key 有效
- 查看浏览器控制台的错误信息

## 📚 相关文档

- [CopilotKit 官方文档](https://docs.copilotkit.ai/)
- [Express.js 文档](https://expressjs.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [VS Code 调试指南](https://code.visualstudio.com/docs/editor/debugging)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个调试示例！

## �� 许可证

MIT License 