/**
 * 直接测试 Action 执行的脚本
 */
const axios = require('axios');

async function testDirectAction() {
  console.log('🧪 开始直接测试 CopilotKit Action...');
  
  const baseUrl = 'http://localhost:3001';
  
  try {
    // 1. 测试健康检查
    console.log('1️⃣ 测试健康检查...');
    const healthResponse = await axios.get(`${baseUrl}/health`);
    console.log('✅ 健康检查成功:', healthResponse.data);
    
    // 2. 测试 CopilotKit 端点
    console.log('\n2️⃣ 测试 CopilotKit 端点...');
    
    const copilotRequest = {
      query: `
        mutation GenerateCopilotResponse($data: GenerateCopilotResponseInput!) {
          generateCopilotResponse(data: $data) {
            threadId
            messages {
              id
              content
              role
            }
          }
        }
      `,
      variables: {
        data: {
          frontend: {
            actions: []
          },
          messages: [
            {
              id: "test-msg-1",
              content: "现在几点了？请使用getCurrentTime函数获取准确时间",
              role: "user"
            }
          ],
          model: "deepseek-chat",
          threadId: "test-thread-" + Date.now()
        }
      }
    };
    
    console.log('📤 发送 GraphQL 请求...');
    const response = await axios.post(`${baseUrl}/api/copilotkit`, copilotRequest, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 30000 // 30秒超时
    });
    
    console.log('📥 收到响应:', JSON.stringify(response.data, null, 2));
    console.log('✅ 测试完成！');
    
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    if (error.response) {
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    }
  }
}

// 运行测试
testDirectAction().catch(console.error); 