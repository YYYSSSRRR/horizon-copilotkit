# CopilotKit Chat - Independent Monorepo

一个基于 CopilotKit 的独立聊天应用，包含前端 React 应用和后端 Python API。

## 项目结构

```
copilot-chat/
├── frontend/          # React + Vite 前端应用
├── backend/           # Python FastAPI 后端
├── packages/          # 本地 CopilotKit 包
│   ├── react-core-next/
│   ├── playwright-actuator/
│   └── shared/
├── scripts/           # 辅助脚本
└── package.json       # Monorepo 配置
```

## 快速开始

### 环境要求

- Node.js >= 18.0.0
- Python >= 3.9.0
- npm >= 8.0.0

### 安装依赖

```bash
# 安装所有依赖
npm run install:all

# 或分别安装
npm install                    # 安装根依赖
npm run install:frontend      # 安装前端依赖
npm run install:backend       # 安装后端依赖
```

### 开发模式

```bash
# 同时启动前端和后端
npm run dev

# 或分别启动
npm run dev:frontend  # 启动前端开发服务器 (http://localhost:5173)
npm run dev:backend   # 启动后端 API 服务器 (http://localhost:8005)
```

### 构建生产版本

```bash
# 构建前端应用
npm run build

# 构建后的文件在 frontend/dist 目录
```

## 可用脚本

- `npm run dev` - 开发模式，同时启动前后端
- `npm run build` - 构建前端生产版本
- `npm run test` - 运行前端测试
- `npm run lint` - 代码检查
- `npm run type-check` - TypeScript 类型检查
- `npm run clean` - 清理构建文件和依赖
- `npm run health` - 检查后端健康状态

## 技术栈

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Tailwind CSS (样式框架)
- CopilotKit React Components

### 后端
- Python 3.9+
- FastAPI (Web 框架)
- CopilotKit Python Runtime

## 配置

### 前端配置
- `frontend/vite.config.ts` - Vite 配置
- `frontend/tailwind.config.js` - Tailwind CSS 配置
- `frontend/tsconfig.json` - TypeScript 配置

### 后端配置
- `backend/server.py` - FastAPI 服务器
- `backend/requirements.txt` - Python 依赖
- `backend/env.example` - 环境变量示例

## 开发注意事项

1. 本项目是独立的 monorepo，不依赖外部 CopilotKit 包
2. 所有必需的 CopilotKit 包都在 `packages/` 目录中
3. 前端默认代理 `/api` 请求到后端 `http://localhost:8005`
4. 支持热重载开发

## 故障排除

### 前端无法启动
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 后端无法启动
```bash
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 端口冲突
- 前端默认端口：5173
- 后端默认端口：8005

如需修改端口，请查看对应的配置文件。

## License

MIT