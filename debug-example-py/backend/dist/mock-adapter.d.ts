/**
 * 模拟适配器 - 用于测试流处理逻辑
 */
import { CopilotServiceAdapter, CopilotRuntimeChatCompletionRequest, CopilotRuntimeChatCompletionResponse } from "@copilotkit/runtime";
export declare class MockAdapter implements CopilotServiceAdapter {
    process(request: CopilotRuntimeChatCompletionRequest): Promise<CopilotRuntimeChatCompletionResponse>;
}
//# sourceMappingURL=mock-adapter.d.ts.map