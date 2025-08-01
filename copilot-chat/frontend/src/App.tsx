import './App.css'
import { Chatbot } from './components/Chatbot'

function App() {
  return (
    <div className="copilotkit-container">
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            欢迎使用 CopilotKit 聊天助手
          </h1>
          
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">产品展示页面</h2>
            <p className="text-gray-600 mb-4">
              这是一个演示页面，展示如何集成 AI 聊天助手到您的应用中。
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">智能助手</h3>
                <p className="text-blue-800 text-sm">
                  AI 驱动的聊天机器人，随时为您提供帮助和支持。
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="font-semibold text-green-900 mb-2">实时对话</h3>
                <p className="text-green-800 text-sm">
                  与 AI 助手进行流畅的实时对话，获得即时回复。
                </p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="font-semibold text-purple-900 mb-2">工具集成</h3>
                <p className="text-purple-800 text-sm">
                  集成各种工具和功能，提供更丰富的交互体验。
                </p>
              </div>
            </div>
            
            <p className="text-gray-500 text-sm">
              点击右下角的聊天按钮开始与 AI 助手对话 💬
            </p>
          </div>
        </div>
        
        {/* Chatbot 组件 */}
        <Chatbot />
      </div>
    </div>
  )
}

export default App 