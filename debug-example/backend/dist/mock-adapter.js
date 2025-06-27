"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MockAdapter = void 0;
const shared_1 = require("@copilotkit/shared");
class MockAdapter {
    async process(request) {
        const { threadId: threadIdFromRequest, messages, actions, eventSource, } = request;
        console.log("🔄 [Mock] Processing request:", {
            threadId: threadIdFromRequest,
            messagesCount: messages.length,
            actionsCount: actions.length,
        });
        const threadId = threadIdFromRequest ?? (0, shared_1.randomUUID)();
        eventSource.stream(async (eventStream$) => {
            console.log("🔄 [Mock] Starting stream processing...");
            try {
                // 模拟工具调用
                if (actions.length > 0) {
                    const actionExecutionId = (0, shared_1.randomUUID)();
                    const actionName = actions[0].name; // 使用第一个可用的 Action
                    console.log("🚀 [Mock] Starting action execution:", actionName);
                    // 开始工具调用
                    eventStream$.sendActionExecutionStart({
                        actionExecutionId,
                        actionName,
                    });
                    // 模拟发送参数
                    console.log("📝 [Mock] Sending action arguments");
                    eventStream$.sendActionExecutionArgs({
                        actionExecutionId,
                        args: JSON.stringify({}),
                    });
                    // 结束工具调用
                    console.log("🔧 [Mock] Ending action execution");
                    eventStream$.sendActionExecutionEnd({
                        actionExecutionId,
                    });
                }
                // 模拟文本响应
                const messageId = (0, shared_1.randomUUID)();
                console.log("💬 [Mock] Starting text message");
                eventStream$.sendTextMessageStart({ messageId });
                // 分块发送文本内容
                const textParts = [
                    "这是一个",
                    "模拟的",
                    "响应消息。",
                    "Action 调用",
                    "应该已经",
                    "成功执行了！"
                ];
                for (let i = 0; i < textParts.length; i++) {
                    console.log(`💬 [Mock] Sending text chunk ${i + 1}:`, textParts[i]);
                    eventStream$.sendTextMessageContent({
                        messageId,
                        content: textParts[i] + (i < textParts.length - 1 ? "" : ""),
                    });
                    // 模拟网络延迟
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                console.log("💬 [Mock] Ending text message");
                eventStream$.sendTextMessageEnd({ messageId });
                console.log("🏁 [Mock] Stream processing completed");
            }
            catch (error) {
                console.error("❌ [Mock] Stream processing error:", error);
                throw error;
            }
            // 🔧 关键：完成事件流
            console.log("🎉 [Mock] Completing event stream");
            eventStream$.complete();
        });
        return { threadId };
    }
}
exports.MockAdapter = MockAdapter;
//# sourceMappingURL=mock-adapter.js.map