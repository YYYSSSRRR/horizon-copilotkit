"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const dotenv = __importStar(require("dotenv"));
// 🔧 加载环境变量
dotenv.config();
// 🔍 调试验证 - 这行会立即执行
console.log("🔍 [DEBUG] server.ts 文件已加载，当前时间:", new Date().toISOString());
console.log("🔑 [DEBUG] DEEPSEEK_API_KEY 状态:", process.env.DEEPSEEK_API_KEY ? `已配置 (${process.env.DEEPSEEK_API_KEY.substring(0, 8)}...)` : "未配置");
console.log("📁 [DEBUG] 工作目录:", process.cwd());
console.log("📁 [DEBUG] __dirname:", __dirname);
const runtime_1 = require("@copilotkit/runtime");
// 🤖 使用 DeepSeek 适配器 - 修复配置
const serviceAdapter = new runtime_1.DeepSeekAdapter({
    apiKey: process.env.DEEPSEEK_API_KEY,
    model: "deepseek-chat",
    // 🔧 关键修复：禁用并行工具调用以提高稳定性
    disableParallelToolCalls: true,
});
// 🎯 定义自定义 Actions
const debugActions = [
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
        handler: async (args) => {
            console.log("🧮 calculateMath Action 被调用，参数:", args);
            try {
                const result = eval(args.expression);
                const response = `计算结果：${args.expression} = ${result}`;
                console.log("🧮 calculateMath 返回结果:", response);
                return response;
            }
            catch (error) {
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
        handler: async (args) => {
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
const runtime = new runtime_1.CopilotRuntime({
    actions: debugActions.map(action => ({
        ...action,
        // 🔧 包装 handler 以确保结果正确处理
        handler: async (...args) => {
            console.log(`🔄 [Wrapper] ${action.name} 开始执行`);
            try {
                const result = await action.handler(...args);
                console.log(`✅ [Wrapper] ${action.name} 执行成功:`, result);
                return result;
            }
            catch (error) {
                console.error(`❌ [Wrapper] ${action.name} 执行失败:`, error);
                throw error;
            }
        }
    }))
});
// 💡 Express 应用设置
const app = (0, express_1.default)();
const PORT = 3001;
// 🔧 添加请求日志中间件
app.use((req, res, next) => {
    console.log(`📡 ${new Date().toISOString()} - ${req.method} ${req.path}`);
    if (req.path.includes('/api/copilotkit')) {
        console.log(`🔗 CopilotKit 请求:`, {
            headers: {
                'content-type': req.headers['content-type'],
                'x-copilotkit-runtime-endpoint': req.headers['x-copilotkit-runtime-endpoint'],
                'x-copilotkit-runtime-action': req.headers['x-copilotkit-runtime-action'],
            },
            bodySize: req.headers['content-length'] || 'unknown'
        });
    }
    next();
});
// ⚡ CORS 配置 - 允许前端访问
app.use((0, cors_1.default)({
    origin: [
        'http://localhost:3000',
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
app.use(express_1.default.json());
// 📡 CopilotKit Runtime 端点 - 添加超时和错误处理
app.use("/api/copilotkit", (0, runtime_1.copilotRuntimeNodeHttpEndpoint)({
    endpoint: "/api/copilotkit",
    runtime,
    serviceAdapter,
}));
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
//# sourceMappingURL=server.js.map