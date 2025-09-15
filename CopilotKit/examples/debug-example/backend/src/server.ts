import express from "express";
import cors from "cors";
import * as dotenv from "dotenv";

// 🔧 加载环境变量
dotenv.config();

// 🔍 调试验证 - 这行会立即执行
console.log("🔍 [DEBUG] server.ts 文件已加载，当前时间:", new Date().toISOString());
console.log("🔑 [DEBUG] DEEPSEEK_API_KEY 状态:", process.env.DEEPSEEK_API_KEY ? `已配置 (${process.env.DEEPSEEK_API_KEY.substring(0, 8)}...)` : "未配置");
console.log("📁 [DEBUG] 工作目录:", process.cwd());
console.log("📁 [DEBUG] __dirname:", __dirname);

import { 
  CopilotRuntime, 
  copilotRuntimeNodeHttpEndpoint,
  OpenAIAdapter
} from "@copilotkit/runtime";
import OpenAI from "openai";


// 🤖 使用 DeepSeek 适配器 - 修复配置
const openai = new OpenAI({
  apiKey: "sk-IGmFA9jyH2mlwcpelXbarOuipa3I55tF4We1fFYiYCElBXhS",
  baseURL: "https://api.chatanywhere.tech/v1"
}) as any; // 添加类型断言解决类型不匹配问题

const serviceAdapter = new OpenAIAdapter({
  openai: openai,
  model: "deepseek-chat",
  // 🔧 关键修复：禁用并行工具调用以提高稳定性
  disableParallelToolCalls: true,
});

// 🎯 定义自定义 Actions
const debugActions: any[] = [
  {
    name: "getCurrentTime",
    description: "获取当前时间",
    parameters: [],
    handler: async () => {
      console.log("🕐 getCurrentTime Action 被调用");
      const currentTime = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
      const result = `当前时间是：${currentTime}`;
      console.log("🕐 getCurrentTime 返回结果:", result);
      return result;
    },
  },
  {
    name: "calculateMath",
    description: "执行数学计算",
    parameters: [
      {
        name: "expression",
        type: "string",
        description: "要计算的数学表达式，如：2+2",
        required: true,
      }
    ],
    handler: async (args: any) => {
      console.log("🧮 calculateMath Action 被调用，参数:", args);
      try {
        const result = eval(args.expression);
        const response = `计算结果：${args.expression} = ${result}`;
        console.log("🧮 calculateMath 返回结果:", response);
        return response;
      } catch (error: any) {
        const errorMsg = `计算错误：${error.message}`;
        console.log("❌ calculateMath 错误:", errorMsg);
        return errorMsg;
      }
    },
  },
  {
    name: "getUserInfo", 
    description: "获取用户信息",
    parameters: [
      {
        name: "userId",
        type: "string",
        description: "用户ID",
        required: true,
      }
    ],
    handler: async (args: any) => {
      console.log("👤 getUserInfo Action 被调用，参数:", args);
      const userInfo = {
        id: args.userId,
        name: `用户${args.userId}`,
        email: `user${args.userId}@example.com`,
        joinDate: "2024-01-01"
      };
      const result = `用户信息：${JSON.stringify(userInfo, null, 2)}`;
      console.log("👤 getUserInfo 返回结果:", result);
      return result;
    },
  },
  {
    name: "debugRuntimeStatus",
    description: "获取运行时调试信息",
    parameters: [],
    handler: async () => {
      console.log("🔧 debugRuntimeStatus Action 被调用");
      const debugInfo = {
        timestamp: new Date().toISOString(),
        nodeVersion: process.version,
        platform: process.platform,
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        env: {
          NODE_ENV: process.env.NODE_ENV,
          DEEPSEEK_API_KEY: process.env.DEEPSEEK_API_KEY ? '已配置' : '未配置'
        }
      };
      const result = `调试信息：\n${JSON.stringify(debugInfo, null, 2)}`;
      console.log("🔧 debugRuntimeStatus 返回结果:", result);
      return result;
    },
  },
];

// 🚀 创建 CopilotRuntime 实例 - 添加明确的结果处理
const runtime = new CopilotRuntime({
  actions: debugActions.map(action => ({
    ...action,
    // 🔧 包装 handler 以确保结果正确处理
    handler: async (...args: any[]) => {
      console.log(`🔄 [Wrapper] ${action.name} 开始执行`);
      try {
        const result = await action.handler(...args);
        console.log(`✅ [Wrapper] ${action.name} 执行成功:`, result);
        return result;
      } catch (error) {
        console.error(`❌ [Wrapper] ${action.name} 执行失败:`, error);
        throw error;
      }
    }
  }))
});
// const runtime = new CopilotRuntime();

// 💡 Express 应用设置
const app = express();
const PORT = 3001;

// 🔧 添加请求日志中间件
// app.use((req, res, next) => {
//   console.log(`📡 ${new Date().toISOString()} - ${req.method} ${req.path}`);
//   if (req.path.includes('/api/copilotkit')) {
//     console.log(`🔗 CopilotKit 请求:`, {
//       headers: {
//         'content-type': req.headers['content-type'],
//         'x-copilotkit-runtime-endpoint': req.headers['x-copilotkit-runtime-endpoint'],
//         'x-copilotkit-runtime-action': req.headers['x-copilotkit-runtime-action'],
//       },
//       bodySize: req.headers['content-length'] || 'unknown'
//     });
//   }
//   next();
// });

// ⚡ CORS 配置 - 允许前端访问
app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://localhost:3002',
    'http://localhost:5173', 
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type', 
    'Authorization',
    'x-copilotkit-runtime-client-gql-version',
    'x-copilotkit-runtime-endpoint',
    'x-copilotkit-runtime-action',
    'x-copilotkit-session-id',
    'x-copilotkit-thread-id',
    'x-copilotkit-run-id',
    'x-copilotkit-properties',
    'x-copilotkit-stream-timeout', // 🔧 添加流超时头
    'Accept',
    'Accept-Encoding',
    'Accept-Language',
    'Cache-Control',
    'Connection',
    'Host',
    'Origin',
    'Referer',
    'User-Agent',
    'X-Requested-With'
  ],
}));

app.use(express.json());

// 📡 CopilotKit Runtime 端点 - 支持LangGraph remote endpoints
app.use("/api/copilotkit", (req, res, next) => {
  // 检查是否启用 LangGraph 模式
  const isLangGraphMode = req.query.langgraph === 'true';
  
  console.log(`🔗 CopilotKit 请求模式: ${isLangGraphMode ? 'LangGraph' : '标准模式'}`);
  
  let currentRuntime;
  if (isLangGraphMode) {
    // LangGraph 模式 - 使用 remote endpoints
    console.log("🐍 启用 LangGraph 模式，连接到 remote endpoint");
    currentRuntime = new CopilotRuntime({
      remoteEndpoints: [
        {
          url: "http://localhost:8001/copilotkit",
        },
      ],
    });
  } else {
    // 标准模式 - 使用本地 actions
    currentRuntime = runtime;
  }
  
  // 正确使用 copilotRuntimeNodeHttpEndpoint
  const yoga = copilotRuntimeNodeHttpEndpoint({
    endpoint: "/api/copilotkit",
    runtime: currentRuntime,
    serviceAdapter,
  });
  
  // 将请求传递给 Yoga 服务器处理
  return yoga(req, res);
});

// 🔧 添加超时处理中间件
app.use("/api/copilotkit", (req, res, next) => {
  // 设置30秒超时
  req.setTimeout(30000, () => {
    console.log("⏰ Request timeout for:", req.path);
    if (!res.headersSent) {
      res.status(408).json({ error: "Request timeout" });
    }
  });
  next();
});

// 🔍 健康检查端点
app.get("/health", (req, res) => {
  res.json({ 
    status: "ok", 
    timestamp: new Date().toISOString(),
    service: "CopilotKit Debug Backend",
    deepseek: process.env.DEEPSEEK_API_KEY ? "configured" : "missing",
    actions: debugActions.map((action) => ({
      name: action.name,
      description: action.description,
      parameters: action.parameters?.length || 0
    }))
  });
});

// 🚀 启动服务器
app.listen(PORT, () => {
  console.log(`🎯 CopilotKit Debug Backend 启动成功！`);
  console.log(`📡 服务器运行在: http://localhost:${PORT}`);
  console.log(`🔗 健康检查: http://localhost:${PORT}/health`);
  console.log(`⚡ CopilotKit 端点: http://localhost:${PORT}/api/copilotkit`);
  console.log(`🤖 DeepSeek 模型: deepseek-chat`);
  console.log(`🔑 API Key 状态: ${process.env.DEEPSEEK_API_KEY ? '✅ 已配置' : '❌ 未配置'}`);
  console.log(`🎯 可用的 Actions: ${debugActions.length}`);
  debugActions.forEach((action, index) => {
    console.log(`   ${index + 1}. ${action.name} - ${action.description}`);
  });
  console.log(`\n💡 前端应用: http://localhost:3000\n`);
}); 