

## 1. 项目安装过程
```bash
cd CopilotKit

pnpm i

pnpm turbo build
```

## 2. 配置.env

## 3. 运行copilot-chat，打开对话框
### 1、启动CopilotKit/packages/copilot-chat/backend
```bash
cd CopilotKit/packages/copilot-chat/backend

python -m venv venv

# Windows: venv\Scripts\activate
source venv/bin/activate 

pip install -r requirements.txt

python server.py
```

### 2、启动CopilotKit/packages/copilot-chat/frontend
```bash
cd CopilotKit/packages/copilot-chat/frontend

npm run dev
```