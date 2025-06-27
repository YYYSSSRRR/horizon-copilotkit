# DeepSeek Adapter for CopilotKit

DeepSeek 适配器为 CopilotKit 提供对 DeepSeek AI 模型的支持。DeepSeek 是一家专注于 AI 研究的公司，提供强大的大语言模型服务。

## 🚀 特性

- ✅ **完整兼容**: 完全兼容 CopilotKit Runtime
- ✅ **流式响应**: 支持实时流式文本生成
- ✅ **工具调用**: 支持并行和串行工具调用
- ✅ **多模型支持**: 支持 DeepSeek 的多个模型
- ✅ **错误处理**: 完善的错误处理和重试机制

## 📦 安装

```bash
npm install @copilotkit/runtime openai
```

## 🔧 使用方法

### 基础用法

```typescript
import { CopilotRuntime, DeepSeekAdapter } from "@copilotkit/runtime";
import OpenAI from "openai";

const deepseek = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: "https://api.deepseek.com/v1",
});

const runtime = new CopilotRuntime({
  // ... 其他配置
});

const adapter = new DeepSeekAdapter({ 
  openai: deepseek 
});
```

### 高级配置

```typescript
const adapter = new DeepSeekAdapter({
  // 使用 API Key 直接初始化
  apiKey: process.env.DEEPSEEK_API_KEY,
  
  // 指定模型
  model: "deepseek-chat", // 或 "deepseek-coder", "deepseek-reasoner"
  
  // 禁用并行工具调用
  disableParallelToolCalls: false,
  
  // 自定义 base URL
  baseURL: "https://api.deepseek.com/v1",
  
  // 自定义请求头
  headers: {
    "Custom-Header": "value"
  }
});
```

### Express.js 集成

```typescript
import express from "express";
import { CopilotRuntime, DeepSeekAdapter, copilotRuntimeNodeHttpEndpoint } from "@copilotkit/runtime";
import OpenAI from "openai";

const app = express();

const deepseek = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: "https://api.deepseek.com/v1",
});

const runtime = new CopilotRuntime({
  actions: [
    // 您的自定义 Actions
  ],
});

app.use("/api/copilotkit", copilotRuntimeNodeHttpEndpoint({
  endpoint: "/api/copilotkit",
  runtime,
  serviceAdapter: new DeepSeekAdapter({ openai: deepseek }),
}));

app.listen(3000);
```

## 🤖 支持的模型

| 模型名称 | 说明 | 适用场景 |
|---------|------|----------|
| `deepseek-chat` | 旗舰对话模型，平衡性能和质量 | 通用聊天、问答、任务执行 |
| `deepseek-coder` | 专门针对代码生成和理解优化 | 代码生成、代码解释、编程辅助 |
| `deepseek-reasoner` | 增强推理能力的模型 | 复杂问题解决、逻辑推理 |

## 🔧 配置选项

### DeepSeekAdapterParams

```typescript
interface DeepSeekAdapterParams {
  /**
   * 预配置的 OpenAI 实例
   */
  openai?: OpenAI;

  /**
   * DeepSeek API Key
   */
  apiKey?: string;

  /**
   * 要使用的模型名称
   * @default "deepseek-chat"
   */
  model?: string;

  /**
   * 是否禁用并行工具调用
   * @default false
   */
  disableParallelToolCalls?: boolean;

  /**
   * 自定义 API 基础 URL
   * @default "https://api.deepseek.com/v1"
   */
  baseURL?: string;

  /**
   * 额外的请求头
   */
  headers?: Record<string, string>;
}
```

## 🌐 环境变量

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

## 🔍 调试

启用调试日志：

```bash
DEBUG=copilotkit:* npm start
```

或在代码中：

```typescript
const adapter = new DeepSeekAdapter({
  apiKey: process.env.DEEPSEEK_API_KEY,
  model: "deepseek-chat"
});

// 监听错误事件
runtime.on('error', (error) => {
  console.error('DeepSeek Adapter Error:', error);
});
```

## 📊 性能优化

### 1. 模型选择

- **通用对话**: 使用 `deepseek-chat`，性能和质量平衡
- **代码相关**: 使用 `deepseek-coder`，专门针对编程优化
- **复杂推理**: 使用 `deepseek-reasoner`，推理能力更强

### 2. 并行工具调用

```typescript
const adapter = new DeepSeekAdapter({
  // 启用并行工具调用（默认）
  disableParallelToolCalls: false,
  // 禁用并行工具调用（顺序执行）
  // disableParallelToolCalls: true,
});
```

### 3. 温度控制

DeepSeek 支持 0.1-2.0 的温度范围：

```typescript
// 在 forwardedParameters 中设置
{
  temperature: 0.7, // 自动限制在 DeepSeek 支持的范围内
}
```

## 🚨 常见问题

### 1. API Key 无效

```
Error: DeepSeek API key is required when openai instance is not provided
```

**解决方案**: 确保设置了正确的 `DEEPSEEK_API_KEY` 环境变量或在配置中提供 `apiKey`。

### 2. 模型不存在

```
Error: The model 'invalid-model' does not exist
```

**解决方案**: 使用支持的模型名称：`deepseek-chat`、`deepseek-coder` 或 `deepseek-reasoner`。

### 3. 网络连接问题

**解决方案**: 
- 检查网络连接
- 确认 `baseURL` 设置正确
- 检查防火墙和代理设置

### 4. 工具调用失败

**解决方案**:
- 检查 Action 定义是否正确
- 验证参数类型和格式
- 查看详细错误日志

## 📚 相关资源

- [DeepSeek 官方网站](https://www.deepseek.com/)
- [DeepSeek API 文档](https://platform.deepseek.com/api-docs/)
- [CopilotKit 官方文档](https://docs.copilotkit.ai/)
- [OpenAI SDK 文档](https://platform.openai.com/docs/libraries/node-js-library)

## 📄 许可证

MIT License - 详见 [LICENSE](../../../../LICENSE) 文件。 