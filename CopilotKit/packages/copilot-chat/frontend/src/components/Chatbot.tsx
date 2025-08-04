import { CopilotKit } from '@copilotkit/react-core-next'
import { ChatbotContent } from './ChatbotContent'

// Chatbot 组件 - 包装 CopilotKit
export function Chatbot(): any {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <ChatbotContent />
    </CopilotKit>
  )
}