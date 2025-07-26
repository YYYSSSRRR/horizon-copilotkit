# Debug Example LangGraph Server

这是一个独立的Python LangGraph服务器，为debug-example提供Human-in-the-Loop功能。

## 快速启动

```bash
# 安装依赖
poetry install

# 设置OpenAI API Key
export OPENAI_API_KEY="your-api-key-here"

# 启动服务器
poetry run langgraph_server
```

服务器将在 http://localhost:8001 启动。

## 功能

- 🗺️ **Human-in-the-Loop**: 真正的LangGraph interrupt/resolve周期
- 🔧 **任务规划**: 生成可执行的步骤列表
- ✅ **用户确认**: 交互式步骤选择和修改
- 🤖 **智能总结**: 基于用户选择的个性化指导

## API端点

- `GET /`: 健康检查
- `GET /healthz`: 服务状态
- `POST /copilotkit`: CopilotKit LangGraph端点

## Agent配置

- **名称**: `debug_human_in_the_loop`
- **描述**: Debug task planning with human-in-the-loop confirmation
- **模型**: GPT-4o-mini (生成步骤) + GPT-4o (最终总结)

## 与前端集成

前端通过URL参数 `?langgraph=true` 切换到LangGraph模式，自动连接到此服务器。