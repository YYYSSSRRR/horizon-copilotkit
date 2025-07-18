/**
 * 直接测试 DeepSeek API 流式响应
 * 帮助诊断流式响应问题
 */
const { DeepSeekAdapter } = require("@copilotkit/runtime");
const dotenv = require("dotenv");

dotenv.config();

async function testDeepSeekStreaming() {
  console.log("🧪 开始测试 DeepSeek 流式响应...");
  
  if (!process.env.DEEPSEEK_API_KEY) {
    console.error("❌ DEEPSEEK_API_KEY 未设置");
    return;
  }

  const adapter = new DeepSeekAdapter({
    apiKey: process.env.DEEPSEEK_API_KEY,
    model: "deepseek-chat",
    disableParallelToolCalls: true,
  });

  // 模拟一个简单的请求
  const mockRequest = {
    threadId: "test-thread-123",
    model: "deepseek-chat",
    messages: [
      {
        id: "test-msg-1",
        content: "现在几点了？",
        role: "user",
        isTextMessage: () => true,
        isActionExecutionMessage: () => false,
        isResultMessage: () => false,
      }
    ],
    actions: [
      {
        name: "getCurrentTime",
        description: "获取当前时间",
        parameters: [],
        handler: async () => {
          const currentTime = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
          const result = `当前时间是：${currentTime}`;
          console.log("🕐 Action 被调用:", result);
          return result;
        },
      }
    ],
    eventSource: {
      stream: async (callback) => {
        console.log("📡 EventSource.stream 被调用");
        
        const mockEventStream = {
          sendTextMessageStart: (data) => {
            console.log("🚀 TextMessageStart:", data);
          },
          sendTextMessageContent: (data) => {
            console.log("💬 TextMessageContent:", data);
          },
          sendTextMessageEnd: (data) => {
            console.log("🏁 TextMessageEnd:", data);
          },
          sendActionExecutionStart: (data) => {
            console.log("🔧 ActionExecutionStart:", data);
          },
          sendActionExecutionArgs: (data) => {
            console.log("📝 ActionExecutionArgs:", data);
          },
          sendActionExecutionEnd: (data) => {
            console.log("✅ ActionExecutionEnd:", data);
          },
          complete: () => {
            console.log("🎉 Stream completed!");
          },
          error: (err) => {
            console.log("❌ Stream error:", err);
          }
        };

        try {
          await callback(mockEventStream);
          console.log("✅ Callback 执行完成");
        } catch (error) {
          console.error("❌ Callback 执行失败:", error);
        }
      }
    },
    forwardedParameters: {}
  };

  try {
    console.log("📤 发送请求到 DeepSeek...");
    const response = await adapter.process(mockRequest);
    console.log("📥 收到响应:", response);
    console.log("✅ 测试完成！");
  } catch (error) {
    console.error("❌ 测试失败:", error);
  }
}

// 运行测试
testDeepSeekStreaming().catch(console.error); 