# 🗺️ LangGraph Human-in-the-Loop 设置指南

## 概述

现在 debug-example 支持两种模式：
- **标准模式**: 使用 Node.js 后端 + DeepSeek，提供基础调试功能
- **LangGraph模式**: 使用 Python LangGraph 后端，提供真正的 Human-in-the-Loop 体验

## 🚀 快速开始

### 1. 启动标准模式

```bash
cd CopilotKit/examples/debug-example
npm run dev
```

访问: http://localhost:3000

### 2. 启动LangGraph模式

#### 步骤1: 启动Python LangGraph服务器

```bash
cd CopilotKit/examples/debug-example/langgraph-server

# 安装依赖 (首次运行)
poetry install

# 启动LangGraph服务器
poetry run langgraph_server
```

服务器将在 http://localhost:8001 启动

#### 步骤2: 启动前端 (另一个终端)

```bash
cd CopilotKit/examples/debug-example  
npm run dev
```

#### 步骤3: 切换到LangGraph模式

访问: http://localhost:3000?langgraph=true

或者在标准模式下点击右上角的 "LangGraph模式" 按钮

## 🔄 两种模式的区别

| 特性 | 标准模式 | LangGraph模式 |
|------|----------|---------------|
| 后端 | Node.js + DeepSeek | Python + LangGraph + OpenAI |
| 功能 | 调试工具Actions | Human-in-the-Loop任务规划 |
| UI | 多功能调试界面 | 专注的任务规划界面 |
| 适用场景 | 调试、工具调用测试 | 任务规划、步骤确认 |

## 💡 LangGraph模式使用示例

进入LangGraph模式后，尝试以下提示：

```
帮我规划学习Python的步骤
```

```
制定一个网站开发计划
```

```
给我一个减肥的行动方案
```

AI会生成具体的步骤列表，然后弹出Human-in-the-Loop界面让你：
- ✅ 选择/取消步骤
- ➕ 添加自定义步骤  
- 🎯 确认后AI继续执行

## 🛠️ 环境要求

### LangGraph模式额外要求

1. **Python 3.12**
2. **Poetry** (Python包管理)
3. **OpenAI API Key** (设置环境变量 `OPENAI_API_KEY`)

### 安装Poetry (如果没有)

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

## 🔧 故障排除

### 常见问题

1. **LangGraph服务器启动失败**
   - 检查Python版本: `python --version` (需要3.12+)
   - 检查OpenAI API Key: `echo $OPENAI_API_KEY`
   - 重新安装依赖: `poetry install --no-cache`

2. **前端连接失败**
   - 确认LangGraph服务器在8001端口运行
   - 检查浏览器控制台错误
   - 确认URL包含 `?langgraph=true`

3. **Human-in-the-Loop界面不显示**
   - 确认使用了 `?langgraph=true` 参数
   - 尝试提示AI生成任务步骤
   - 检查浏览器开发者工具的网络请求

## 📁 项目结构

```
debug-example/
├── frontend/                 # React前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── HomePage.tsx         # 标准模式
│   │   │   └── HumanInTheLoopPage.tsx  # LangGraph模式
│   │   └── App.tsx           # 模式路由
├── backend/                  # Node.js后端 (标准模式)
└── langgraph-server/         # Python LangGraph后端
    ├── debug_langgraph/
    │   ├── server.py
    │   └── human_in_the_loop_agent.py
    └── pyproject.toml
```

## 🎯 技术实现

LangGraph模式实现了真正的Human-in-the-Loop工作流：

1. **AI生成步骤** → `generate_task_steps` 工具调用
2. **LangGraph中断** → `interrupt()` 暂停执行  
3. **前端渲染** → `useLangGraphInterrupt` 显示界面
4. **用户确认** → `resolve()` 继续工作流
5. **AI总结** → 基于用户选择生成指导

这提供了与原生LangGraph完全一致的体验！