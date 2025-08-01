import { useMemo } from 'react'
import { useCopilotAction, useCopilotScriptAction } from '@copilotkit/react-core-next'
import { askLlmAction, fillFormAction } from '../../playwright-scripts/index.js'

/**
 * 业务相关的 CopilotKit Actions
 * 在这里定义与业务项目相关的 AI 动作
 */
export function useBusinessActions() {
  // 注册前端 Action 来测试工具调用
  const notificationAction = useMemo(() => ({
    name: "showNotification",
    description: "显示前端通知消息",
    parameters: [
      {
        name: "message",
        description: "通知消息内容",
        type: "string",
        required: true,
      },
      {
        name: "type",
        description: "通知类型: success, error, warning, info",
        type: "string",
        required: false,
      },
    ],
    handler: async (args: any) => {
      const { message, type = "info" } = args;
      alert(`${type.toUpperCase()}: ${message}`);
      return `已显示通知: ${message}`;
    },
  }), []);

  useCopilotAction(notificationAction);

  useCopilotScriptAction(askLlmAction);
  useCopilotScriptAction(fillFormAction);
}