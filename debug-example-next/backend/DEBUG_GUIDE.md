# CopilotKit Backend 调试指南

## 🚀 快速启动

### 1. 使用 VS Code 调试

推荐使用 VS Code 的调试功能：

1. 打开 VS Code
2. 按 `Ctrl+Shift+D` 打开调试面板
3. 选择 **"Debug CopilotKit Backend (Debug Port)"** 配置
4. 点击绿色播放按钮或按 `F5` 开始调试

### 2. 手动启动服务器

```bash
cd debug-example-next/backend
source venv/bin/activate
SERVER_PORT=8007 python server_py.py
```

## 🔍 调试端点

### 基础端点测试

```bash
# 健康检查
curl http://localhost:8007/api/copilotkit/api/health

# CopilotKit Hello
curl http://localhost:8007/api/copilotkit/copilotkit/hello

# 列出动作
curl http://localhost:8007/api/copilotkit/api/actions

# API 文档
open http://localhost:8007/docs
```

### 流式聊天测试

```bash
curl -X POST http://localhost:8007/api/copilotkit/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello", "id": "msg_1"}]}'
```

### 动作执行测试

```bash
# 获取当前时间
curl -X POST http://localhost:8007/api/copilotkit/api/actions/execute \
  -H "Content-Type: application/json" \
  -d '{"action_name": "get_current_time", "arguments": {"timezone": "UTC"}}'

# 计算表达式
curl -X POST http://localhost:8007/api/copilotkit/api/actions/execute \
  -H "Content-Type: application/json" \
  -d '{"action_name": "calculate", "arguments": {"expression": "2+3*4"}}'
```

## 🛠️ 调试配置

### VS Code 调试配置

项目包含以下调试配置：

1. **Debug CopilotKit Backend Server** (端口 8005)
2. **Debug CopilotKit Backend (Debug Port)** (端口 8007) - 推荐
3. **Debug CopilotKit Backend (Global venv)** (全局虚拟环境)
4. **Debug CopilotKit Backend (System Python)** (系统 Python)

### 环境变量

```bash
# 必需的环境变量
export DEEPSEEK_API_KEY="your-api-key"
export DEEPSEEK_MODEL="deepseek-chat"
export SERVER_PORT="8007"

# 可选的环境变量
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export PYTHONPATH="/path/to/runtime-python:$PYTHONPATH"
```

## 🔧 常见问题解决

### 1. 端口被占用

```bash
# 查找占用端口的进程
lsof -ti:8007

# 杀死占用端口的进程
lsof -ti:8007 | xargs kill -9
```

### 2. 导入错误

确保 Python 路径正确：

```bash
export PYTHONPATH="/path/to/CopilotKit/packages/runtime-python:$PYTHONPATH"
```

### 3. 虚拟环境问题

```bash
# 重新创建虚拟环境
cd debug-example-next/backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 调试器无法进入断点

- 确保使用正确的调试配置
- 检查端口是否正确 (8007)
- 确保虚拟环境路径正确
- 检查 PYTHONPATH 设置

## 📋 API 路由

服务器支持以下路由（带 `/api/copilotkit` 前缀）：

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/copilotkit/api/health` | 健康检查 |
| POST | `/api/copilotkit/api/chat` | 非流式聊天 |
| POST | `/api/copilotkit/api/chat/stream` | 流式聊天 |
| GET | `/api/copilotkit/api/actions` | 列出动作 |
| POST | `/api/copilotkit/api/actions/execute` | 执行动作 |
| GET | `/api/copilotkit/copilotkit/hello` | CopilotKit Hello |
| GET | `/api/copilotkit/copilotkit/agents` | 获取代理 |

## 🎯 前端集成

前端应该发送请求到：
- 基础URL: `http://localhost:8007`
- 流式聊天: `http://localhost:8007/api/copilotkit/api/chat/stream`

## 📝 日志调试

服务器日志保存在：
- 控制台输出
- `backend.log` 文件

查看实时日志：
```bash
tail -f backend.log
```

## 🔍 断点调试技巧

1. **在关键函数设置断点**：
   - `create_demo_actions()` - 动作创建
   - `chat_stream()` - 流式聊天处理
   - `execute_action()` - 动作执行

2. **检查变量**：
   - `request` - 请求数据
   - `messages` - 消息列表
   - `runtime` - 运行时实例

3. **调试流程**：
   - 请求接收 → 消息转换 → 服务适配器 → 响应生成

## 🚨 故障排除

如果遇到 500 错误：

1. 检查服务器日志
2. 确保所有依赖已安装
3. 检查 API 密钥配置
4. 验证请求格式
5. 使用调试器逐步执行

## 📞 支持

如果问题仍然存在：
1. 检查 `backend.log` 文件
2. 使用 VS Code 调试器
3. 查看控制台输出
4. 测试单个端点 