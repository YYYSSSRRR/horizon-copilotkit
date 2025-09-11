import { useState, useEffect, useMemo, useCallback } from 'react'
import { 
  useCopilotChat, 
  useCopilotAction,
  useCopilotScriptAction, 
  useCopilotReadable,
  useToast,
  useFrontendApprovalManager,
  TextMessage, 
  FrontendAction
} from '@copilotkit/react-core-next'
import { askLlmAction, fillFormAction } from '../../playwright-scripts/index.js'


export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<string>('检查中...')
  const [currentTime, setCurrentTime] = useState<string>('')
  const [userInfo, setUserInfo] = useState<string>('')
  const [systemStatus, setSystemStatus] = useState<string>('')
  
  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    age: '',
    gender: '',
    country: '',
    skills: [] as string[],
    bio: '',
    newsletter: false,
    priority: 'medium',
    startDate: '',
    endDate: ''
  })

  const { toast } = useToast()
  const approvalManager = useFrontendApprovalManager()
  
  // 表单处理函数
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    toast(`表单已提交！姓名: ${formData.name}`, 'success')
    console.log('表单数据:', formData)
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSkillToggle = (skill: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.includes(skill)
        ? prev.skills.filter(s => s !== skill)
        : [...prev.skills, skill]
    }))
  }

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      age: '',
      gender: '',
      country: '',
      skills: [],
      bio: '',
      newsletter: false,
      priority: 'medium',
      startDate: '',
      endDate: ''
    })
    toast('表单已重置', 'info')
  }
  
  // 检查后端状态
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch('/api/copilotkit/api/health')
        if (response.ok) {
          const data = await response.json()
          setBackendStatus(`✅ 后端正常运行 (${data.adapter?.provider}: ${data.adapter?.model})`)
        } else {
          setBackendStatus('❌ 后端连接失败')
        }
      } catch (error) {
        console.log(error,"后端不可用");
        setBackendStatus('❌ 后端不可用')
      }
    }
    checkBackend()
  }, [])

  // 缓存动作处理器
  const timeHandler = useCallback(async (args: any) => {
    const { timezone } = args || {}
    const result = `当前时间: ${new Date().toLocaleString('zh-CN', { 
      timeZone: timezone || 'Asia/Shanghai' 

    })}`
    setCurrentTime(result)
    toast('时间查询成功！', 'success')
    return result
  }, [setCurrentTime, toast])


  // 定义Copilot动作 - 时间查询
  const timeAction = useMemo(() => ({
    name: "get_current_time",
    description: "获取当前时间",
    parameters: [
      {
        name: "timezone",
        type: "string",
        description: "时区 (默认: Asia/Shanghai)",
        required: false
      }
    ],
    handler: timeHandler
  }), [timeHandler])

  useCopilotAction(timeAction)



  // 注册前端 Action 来测试工具调用
  
  const notificationHandler=useCallback(async (args:{ message: string; type?: string })=>{
      const { message, type = "info" } = args || {};
      alert(`${type.toUpperCase()}: ${message}`);
      return `已显示通知: ${message}`;
  },[])

  const notificationAction = useMemo<FrontendAction<[
    { name: "message"; type: "string"; description: string; required: true },
    { name: "type"; type: "string"; description: string; required: false }
  ]>>(() => ({
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
    handler: notificationHandler
  }), [notificationHandler]);

  useCopilotAction(notificationAction);

  // 需要审批的表单提交动作
  const submitFormHandler = useCallback(async (args: { formData?: any }) => {
    const { formData: submittedData } = args || {};
    const dataToSubmit = submittedData || formData;
    
    // 模拟表单提交
    console.log('提交表单数据:', dataToSubmit);
    toast(`表单提交成功！用户: ${dataToSubmit.name || '未知'}`, 'success');
    
    // 模拟提交到服务器
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return `表单提交成功！已提交用户 ${dataToSubmit.name || '未知'} 的信息。`;
  }, [formData, toast]);

  const submitFormAction = useMemo<FrontendAction<[
    { name: "formData"; type: "object"; description: string; required: false }
  ]>>(() => ({
    name: "submitForm",
    description: "提交用户表单数据（需要审批）",
    requireApproval: true, // 启用审批
    parameters: [
      {
        name: "formData",
        type: "object",
        description: "要提交的表单数据，如果不提供则使用当前表单内容",
        required: false,
      },
    ],
    handler: submitFormHandler
  }), [submitFormHandler]);

  useCopilotAction(submitFormAction);

  // 需要审批的表单重置动作
  const resetFormHandler = useCallback(async (args: { confirm?: boolean }) => {
    const { confirm = false } = args || {};
    
    if (confirm) {
      resetForm();
      return '表单已重置为默认值。';
    } else {
      return '请确认是否要重置表单。使用 confirm: true 参数来确认操作。';
    }
  }, [resetForm]);

  const resetFormAction = useMemo<FrontendAction<[
    { name: "confirm"; type: "boolean"; description: string; required: false }
  ]>>(() => ({
    name: "resetFormData",
    description: "重置表单数据（需要审批）",
    requireApproval: true, // 启用审批
    parameters: [
      {
        name: "confirm",
        type: "boolean",
        description: "确认重置表单，设为 true 来确认操作",
        required: false,
      },
    ],
    handler: resetFormHandler
  }), [resetFormHandler]);

  useCopilotAction(resetFormAction);

  // 前端审批决定处理动作
  const frontendApprovalHandler = useCallback(async (args: { decision: string; approval_id?: string }) => {
    const { decision, approval_id } = args || {};
    
    if (!approvalManager) {
      return `❌ 审批管理器未初始化，无法处理审批请求。`;
    }
    
    const normalizedDecision = decision?.toLowerCase()?.trim() || '';
    const isApproved = ['y', 'yes', '同意', '是', 'approve', 'approved'].includes(normalizedDecision);
    const isRejected = ['n', 'no', '拒绝', '否', 'reject', 'rejected'].includes(normalizedDecision);
    
    if (!isApproved && !isRejected) {
      return `❌ 无效的审批决定: "${decision}"。请输入 'y'/'yes'/'同意'/'是' 批准，或 'n'/'no'/'拒绝'/'否' 拒绝。`;
    }
    
    // 查找审批请求
    const request = approvalManager.findApprovalByPartialId(approval_id || "");
    if (!request) {
      const pending = approvalManager.getPendingApprovals();
      return pending.length > 0
        ? `❌ 找不到匹配的审批请求。当前有 ${pending.length} 个待处理的审批。`
        : '❌ 没有找到待审批的请求。';
    }
    
    if (request.resolved) {
      return `❌ 审批请求 ${request.approvalId.slice(-8)} 已经被处理过了。`;
    }
    
    // 标记为已解决
    request.resolved = true;
    
    if (isApproved) {
      // 批准后，根据动作名称执行相应的操作
      try {
        if (request.actionName === 'submitForm') {
          // 执行表单提交，使用审批请求中保存的参数
          const result = await submitFormHandler(request.parameters);
          return `✅ 批准 - ${result}`;
        } else if (request.actionName === 'resetFormData') {
          // 执行表单重置
          const result = await resetFormHandler({ confirm: true });
          return `✅ 批准 - ${result}`;
        } else if (request.actionName === 'fill-form') {
          // 执行表单填写脚本动作
          try {
            const module: { fillFormExecutor: (formData: any) => Promise<string> } = 
              await import('../../playwright-scripts/executors/fill-form.executor.js');
            const { fillFormExecutor } = module;
            const result = await fillFormExecutor(request.parameters);
            return `✅ 批准 - 脚本动作执行完成: ${result}`;
          } catch (error) {
            return `❌ 脚本动作执行失败: ${error}`;
          }
        } else {
          return `✅ 批准 - 前端动作 "${request.actionName}" 已获批准，但暂未实现执行逻辑。`;
        }
      } catch (error) {
        return `❌ 执行失败 - 审批已通过，但操作执行时出错: ${error}`;
      }
    } else {
      return `❌ 拒绝 - 前端动作 "${request.actionName}" 已被拒绝，操作已取消。`;
    }
  }, [approvalManager, submitFormHandler, resetFormHandler]);

  const frontendApprovalAction = useMemo<FrontendAction<[
    { name: "decision"; type: "string"; description: string; required: true },
    { name: "approval_id"; type: "string"; description: string; required: false }
  ]>>(() => ({
    name: "handleFrontendApproval",
    description: "【重要】只有当用户在最新消息中明确输入了'y'、'yes'、'同意'、'是'、'n'、'no'、'拒绝'、'否'等审批决定时，才能调用此工具。绝对不要在显示审批消息后立即调用此工具，必须等待用户的实际回复。如果用户没有明确输入审批决定，就不要调用此工具。",
    parameters: [
      {
        name: "decision",
        type: "string",
        description: "用户在最新消息中明确输入的审批决定，必须是以下值之一: 'y', 'yes', '同意', '是', 'n', 'no', '拒绝', '否'。只有用户真正输入了这些词时才使用。",
        required: true,
      },
      {
        name: "approval_id",
        type: "string", 
        description: "可选的审批ID（部分即可），如果不提供则处理最新的审批请求",
        required: false,
      },
    ],
    handler: frontendApprovalHandler
  }), [frontendApprovalHandler]);

  useCopilotAction(frontendApprovalAction);

  useCopilotScriptAction(askLlmAction);
  useCopilotScriptAction(fillFormAction);

  // 使用CopilotChat
  const { 
    visibleMessages, 
    appendMessage, 
    setMessages, 
    reloadMessages,
    stopGeneration,
    isLoading 
  } = useCopilotChat()

  // 让Copilot了解当前页面内容 - 使用 useMemo 避免无限循环
  const readableDescription = useMemo(() => "调试页面信息和状态", []);
  const readableValue = useMemo(() => `
    这是一个CopilotKit调试示例页面。
    当前状态:
    - 后端状态: ${backendStatus}
    - 最新时间查询: ${currentTime}
    - 用户信息: ${userInfo}
    - 系统状态: ${systemStatus}
    
    可用功能:
    1. 获取当前时间 (get_current_time) - 前端处理，无需审批
    2. 数学计算 (calculate) - 后端审批系统处理
    3. 查询用户信息 (get_user_info) - 后端审批系统处理
    4. 检查系统状态 (check_status) - 后端审批系统处理
    5. 显示通知消息 (showNotification) - 前端处理，无需审批
    6. 提交表单数据 (submitForm) - 前端处理，需要审批
    7. 重置表单数据 (resetFormData) - 前端处理，需要审批
    8. 处理审批决定 (handleFrontendApproval) - 用于前端审批流程
  `, [backendStatus, currentTime, userInfo, systemStatus])

  useCopilotReadable({
    description: readableDescription,
    value: readableValue,
    dependencies: [readableDescription, readableValue]
  })

  const handleSendMessage = (message: string) => {
    if (message.trim()) {
      console.log("发送消息前")
      appendMessage(new TextMessage({ content: message, role: 'user' }))
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-2 sm:p-4">
      {/* 头部 */}
      <header className="max-w-7xl mx-auto mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🚀 CopilotKit Debug Example Next
        </h1>
        <p className="text-gray-600">
          基于 react-core-next 和 runtime-next 的调试示例
        </p>
        <div className="mt-4 p-3 bg-white rounded-lg shadow">
          <span className="text-sm font-medium text-gray-700">后端状态: </span>
          <span className="text-sm">{backendStatus}</span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6">
        {/* 表单区域 */}
        <div className="lg:col-span-4">
          <UserInfoForm 
            formData={formData}
            onInputChange={handleInputChange}
            onSkillToggle={handleSkillToggle}
            onSubmit={handleFormSubmit}
            onReset={resetForm}
          />
        </div>

        {/* 聊天区域 */}
        <div className="lg:col-span-5">
          <div className="bg-white rounded-lg shadow-lg h-[600px] flex flex-col">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold">💬 AI 助手聊天</h2>
              <p className="text-sm text-gray-600">
                尝试说: "现在几点了？" 或 "计算 2+3*4" 或 "检查系统状态"
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {visibleMessages.map((message, index) => {
                console.log("Message:", message, message.status?.code);
                
                // 显示文本消息和工具执行结果
                let content = '';
                let role = 'assistant'; // 默认为助手角色
                
                if (message.isTextMessage()) {
                  const textMsg = message as any;
                  content = textMsg.content;
                  role = textMsg.role || 'assistant';
                } else if (message.isResultMessage?.()) {
                  const resultMsg = message as any;
                  content = resultMsg.result || '工具执行完成';
                  role = 'assistant'; // 工具结果显示为助手消息
                } else if (message.isActionExecutionMessage?.()) {
                  // 跳过工具执行消息，只显示结果
                  return null;
                } else {
                  // 尝试显示其他类型的消息
                  const anyMsg = message as any;
                  content = anyMsg.content || anyMsg.result || JSON.stringify(message, null, 2);
                  role = anyMsg.role || 'assistant';
                }

                if (!content) return null;
                
                return (
                  <div
                    key={index}
                    className={`flex ${
                      role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-800'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{content}</p>
                    </div>
                  </div>
                );
              })}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 px-4 py-2 rounded-lg">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-100"></div>
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t">
              <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
              {isLoading && (
                <button
                  onClick={stopGeneration}
                  className="mt-2 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                >
                  停止生成
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 侧边栏 - 状态信息 */}
        <div className="lg:col-span-3 space-y-4">
          {/* 快速操作 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">🎮 快速操作</h3>
            <div className="space-y-2">
              <button
                onClick={() => handleSendMessage("现在几点了？")}
                className="w-full px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                获取时间
              </button>
              <button
                onClick={() => handleSendMessage("计算 15*8+24")}
                className="w-full px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600"
              >
                数学计算
              </button>
              <button
                onClick={() => handleSendMessage("查看我的用户信息")}
                className="w-full px-3 py-2 text-sm bg-purple-500 text-white rounded hover:bg-purple-600"
              >
                用户信息
              </button>
                <button
                  onClick={() => handleSendMessage("检查系统状态")}
                  className="w-full px-3 py-2 text-sm bg-orange-500 text-white rounded hover:bg-orange-600"
                >
                  系统状态
                </button>
                <button
                  onClick={() => handleSendMessage("显示通知消息")}
                  className="w-full px-3 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                >
                  显示通知
                </button>
                <button
                  onClick={() => handleSendMessage("提交当前表单数据")}
                  className="w-full px-3 py-2 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600"
                >
                  提交表单 (需审批)
                </button>
                <button
                  onClick={() => handleSendMessage("重置表单数据")}
                  className="w-full px-3 py-2 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600"
                >
                  重置表单 (需审批)
                </button>
            </div>
          </div>

          {/* 实时状态 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">📊 实时状态</h3>
            <div className="space-y-3 text-sm">
              {currentTime && (
                <div>
                  <span className="font-medium text-blue-600">⏰ 时间:</span>
                  <p className="text-gray-700 mt-1">{currentTime}</p>
                </div>
              )}
              
              
              {userInfo && (
                <div>
                  <span className="font-medium text-purple-600">👤 用户:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{userInfo}</p>
                </div>
              )}
              
              {systemStatus && (
                <div>
                  <span className="font-medium text-orange-600">🔧 状态:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{systemStatus}</p>
                </div>
              )}
            </div>
          </div>

          {/* 消息控制 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">🔧 消息控制</h3>
            <div className="space-y-2">
              <button
                onClick={() => setMessages([])}
                className="w-full px-3 py-2 text-sm bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                清空对话
              </button>
              <button
                onClick={() => reloadMessages('')}
                className="w-full px-3 py-2 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600"
              >
                重新加载
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}

// 聊天输入组件
function ChatInput({ onSendMessage, disabled }: { onSendMessage: (message: string) => void, disabled: boolean }) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message)
      setMessage('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex space-x-2">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="输入消息..."
        disabled={disabled}
        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        发送
      </button>
    </form>
  )
}

// 用户信息表单组件
function UserInfoForm({ 
  formData, 
  onInputChange, 
  onSkillToggle, 
  onSubmit, 
  onReset 
}: {
  formData: any,
  onInputChange: (field: string, value: any) => void,
  onSkillToggle: (skill: string) => void,
  onSubmit: (e: React.FormEvent) => void,
  onReset: () => void
}) {
  const skillOptions = ['React', 'TypeScript', 'Node.js', 'Python', 'Java', 'Go'];
  const countryOptions = ['中国', '美国', '日本', '德国', '法国', '英国'];

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6 h-fit">
      <h2 className="text-lg font-semibold mb-4">📝 用户信息表单</h2>
      <p className="text-sm text-gray-600 mb-4">
        这个表单用于测试 ScriptAction 的界面操作功能
      </p>
      
      <form onSubmit={onSubmit} className="space-y-4">
        {/* 姓名和邮箱 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              姓名 *
            </label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={(e) => onInputChange('name', e.target.value)}
              placeholder="请输入您的姓名"
              aria-label="姓名输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              邮箱 *
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={(e) => onInputChange('email', e.target.value)}
              placeholder="请输入您的邮箱"
              aria-label="邮箱输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
        </div>

        {/* 年龄和国家 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-1">
              年龄
            </label>
            <input
              id="age"
              name="age"
              type="number"
              min="1"
              max="150"
              value={formData.age}
              onChange={(e) => onInputChange('age', e.target.value)}
              placeholder="请输入您的年龄"
              aria-label="年龄输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-1">
              国家
            </label>
            <select
              id="country"
              name="country"
              value={formData.country}
              onChange={(e) => onInputChange('country', e.target.value)}
              aria-label="国家选择"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">请选择国家</option>
              {countryOptions.map(country => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 性别和优先级 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">性别</label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="male"
                  checked={formData.gender === 'male'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="男性"
                  className="mr-2"
                />
                男
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="female"
                  checked={formData.gender === 'female'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="女性"
                  className="mr-2"
                />
                女
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="other"
                  checked={formData.gender === 'other'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="其他"
                  className="mr-2"
                />
                其他
              </label>
            </div>
          </div>
          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              优先级
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={(e) => onInputChange('priority', e.target.value)}
              aria-label="优先级选择"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </div>
        </div>


        {/* 技能多选框 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">技能</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {skillOptions.map(skill => (
              <label key={skill} className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.skills.includes(skill)}
                  onChange={() => onSkillToggle(skill)}
                  aria-label={`技能: ${skill}`}
                  className="mr-2"
                />
                {skill}
              </label>
            ))}
          </div>
        </div>


        {/* 日期范围 */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
              开始日期
            </label>
            <input
              id="startDate"
              name="startDate"
              type="date"
              value={formData.startDate}
              onChange={(e) => onInputChange('startDate', e.target.value)}
              aria-label="开始日期"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
              结束日期
            </label>
            <input
              id="endDate"
              name="endDate"
              type="date"
              value={formData.endDate}
              onChange={(e) => onInputChange('endDate', e.target.value)}
              aria-label="结束日期"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* 个人简介文本区域 */}
        <div>
          <label htmlFor="bio" className="block text-sm font-medium text-gray-700 mb-1">
            个人简介
          </label>
          <textarea
            id="bio"
            name="bio"
            rows={3}
            value={formData.bio}
            onChange={(e) => onInputChange('bio', e.target.value)}
            placeholder="请简单介绍一下自己..."
            aria-label="个人简介"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* 通讯录订阅复选框 */}
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.newsletter}
              onChange={(e) => onInputChange('newsletter', e.target.checked)}
              aria-label="订阅通讯录"
              className="mr-2"
            />
            订阅通讯录
          </label>
        </div>

        {/* 按钮组 */}
        <div className="flex space-x-2 pt-4">
          <button
            type="submit"
            aria-label="提交表单"
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            提交
          </button>
          <button
            type="button"
            onClick={onReset}
            aria-label="重置表单"
            className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            重置
          </button>
        </div>
      </form>

      {/* 表单数据预览 */}
      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <h3 className="text-sm font-medium text-gray-700 mb-2">当前表单数据:</h3>
        <pre className="text-xs text-gray-600 overflow-auto max-h-32">
          {JSON.stringify(formData, null, 2)}
        </pre>
      </div>
    </div>
  )
} 