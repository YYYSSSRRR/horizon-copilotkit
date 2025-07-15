# CopilotKit Runtime Python

CopilotKit的Python运行时，基于FastAPI，无GraphQL依赖。

## 特性

- 🚀 基于FastAPI的高性能异步运行时
- 🔄 使用RxPY替代RxJS，保持功能逻辑一致性
- 📡 支持流式响应和事件源
- 🧩 与react-core-next无缝对接
- 🔌 支持DeepSeek等AI服务适配器
- 📝 完整的类型系统支持

## 安装

```bash
pip install -e .
```

## 快速开始

```python
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter

# 创建运行时实例
runtime = CopilotRuntime()

# 配置DeepSeek适配器
deepseek_adapter = DeepSeekAdapter(
    api_key="your-deepseek-api-key",
    model="deepseek-chat"
)

runtime.use(deepseek_adapter)

# 启动FastAPI服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(runtime.app, host="0.0.0.0", port=8000)
```

## 架构对比

| TypeScript Runtime | Python Runtime |
|-------------------|----------------|
| GraphQL + Express | FastAPI + REST |
| RxJS | RxPY |
| TypeScript类型 | Pydantic模型 |
| Node.js事件循环 | AsyncIO |

## 目录结构

```
copilotkit_runtime/
├── adapters/           # 服务适配器
│   └── deepseek/      # DeepSeek适配器
├── core/              # 核心功能
├── streaming/         # 流式处理
├── types/             # 类型定义
└── utils/             # 工具函数
``` 