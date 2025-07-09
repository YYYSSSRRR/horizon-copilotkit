# @copilotkit/react-core-next

下一代 CopilotKit React 核心库，采用 REST API + WebSocket 架构，移除了 GraphQL 依赖。

## 特性

- 🚀 **轻量级**: 移除 GraphQL 依赖，减少包体积
- 🔧 **简单易用**: 保持与 react-core 相同的 Hook API
- ⚡ **高性能**: 直接 JSON 序列化，减少转换开销
- 🌐 **标准协议**: 基于 REST API + WebSocket，易于调试
- 🔄 **向后兼容**: 平滑迁移路径

## 安装

```bash
npm install @copilotkit/react-core-next
```

## 快速开始

```tsx
import { CopilotKit, useCopilotChat } from "@copilotkit/react-core-next";

function App() {
  return (
    <CopilotKit runtimeUrl="http://localhost:8000">
      <ChatComponent />
    </CopilotKit>
  );
}

function ChatComponent() {
  const { appendMessage, messages, isLoading } = useCopilotChat();
  
  return (
    <div>
      {/* 您的聊天 UI */}
    </div>
  );
}
```

## 主要功能

### 🔥 核心 Hooks
- `useCopilotChat` - 聊天功能，支持流式响应
- `useCopilotAction` - 注册自定义动作
- `useCopilotReadable` - 提供上下文信息  
- `useCoAgent` - CoAgent 管理
- `useCopilotRuntimeClient` - 运行时客户端访问

### 🛠️ 扩展 Hooks
- `useMakeCopilotDocumentReadable` - 文档可读化
- `useCopilotAdditionalInstructions` - 额外指令管理
- `useCoAgentStateRender` - CoAgent 状态渲染器
- `useChat` - 底层聊天功能（更复杂的实现）
- `useLangGraphInterrupt` - LangGraph 中断处理
- `useLangGraphInterruptRender` - LangGraph 中断界面渲染

### 🧩 组件
- `CopilotKit` - 主要的 Provider 组件（内置 Toast 和错误边界）
- `ToastProvider` & `useToast` - 通知提示系统
- `CopilotErrorBoundary` - 错误边界组件

### ⚡ 客户端层
- REST API 客户端
- WebSocket 流式客户端  
- 统一运行时客户端（自动选择最佳传输方式）
- 错误处理和重试机制

## 主要改进

- **移除 GraphQL**: 使用标准 REST API + WebSocket
- **更小的包体积**: 减少 60-70% 的依赖
- **更好的调试体验**: 标准 HTTP 协议
- **更快的启动时间**: 无 GraphQL 解析开销

## 迁移指南

从 `@copilotkit/react-core` 迁移只需要更改导入：

```tsx
// 之前
import { CopilotKit, useCopilotChat } from "@copilotkit/react-core";

// 之后
import { CopilotKit, useCopilotChat } from "@copilotkit/react-core-next";
```

API 完全兼容，无需修改其他代码。 