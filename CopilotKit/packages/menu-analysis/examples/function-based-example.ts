#!/usr/bin/env tsx

/**
 * 函数式菜单导航分析示例
 * 演示如何使用转换器和函数式页面打开功能
 */

// Import polyfills first
import '../polyfills.js';

// Load environment variables from .env file
import dotenv from 'dotenv';
import path from 'path';

// Load .env file from the project root
dotenv.config({ path: path.join(__dirname, '..', '.env') });

// 使用 TypeScript 导入
import { 
  createDefaultConfig,
  MenuAnalysisEngine,
  MenuItem,
  MenuFunctionality
} from '../src';
import { SimpleTransformer } from '../src/menu-transformers';

// 现在使用 SimpleTransformer
async function transformMenuConfig(filePath: string): Promise<MenuItem[]> {
  return await SimpleTransformer.transformFromJsonFile(filePath);
}

function filterWithEmit(menuItems: MenuItem[]): MenuItem[] {
  return SimpleTransformer.filterWithEmit(menuItems);
}


/**
 * 菜单打开回调函数 - 这是核心的函数式导航实现
 */
async function handleMenuOpen(emit: string[], menuItem: MenuItem): Promise<void> {
  console.log(`📱 通过函数打开菜单: ${menuItem.text}`);
  console.log(`   Emit 动作: [${emit.map(e => `"${e}"`).join(', ')}]`);
  
  // 这里实现你的具体菜单打开逻辑
  for (let i = 0; i < emit.length; i++) {
    const action = emit[i];
    console.log(`   🔧 执行动作 ${i + 1}: ${action}`);
    
    try {
      // 尝试解析JSON格式的动作
      const actionData = JSON.parse(action);
      
      if (actionData.Href) {
        console.log(`      🔗 导航到页面: ${actionData.Href}`);
      } else if (actionData.Action) {
        console.log(`      ⚡ 执行业务动作: ${actionData.Action}`);
      } else if (actionData.CmdId) {
        console.log(`      🖥️ 执行系统命令: ${actionData.CmdId}`);
      } else {
        console.log(`      📄 执行复合动作: ${JSON.stringify(actionData)}`);
      }
      
    } catch (e) {
      // 不是JSON格式的动作，直接作为字符串处理
      if (action === 'jumpSPAPage') {
        console.log(`      📄 准备跳转到SPA页面`);
      } else if (action === 'jump2QueryHdDlg') {
        console.log(`      📊 准备打开查询对话框`);
      } else if (action === 'openTransNeWebServiceTaskManageProgress') {
        console.log(`      📈 打开网管任务管理进度`);
      } else {
        console.log(`      📝 执行自定义动作: ${action}`);
      }
    }
  }
  
  // 模拟等待页面加载完成
  console.log(`   ⏳ 等待页面加载...`);
  await new Promise(resolve => setTimeout(resolve, 800));
  console.log(`   ✅ 页面加载完成\n`);
}

/**
 * 使用 MenuAnalysisEngine 完整分析所有菜单
 */
async function analyzeFullMenuTree(): Promise<MenuFunctionality[]> {
  try {
    console.log('🌳 完整菜单树分析示例...');

    // 加载菜单配置
    const configPath = path.join(__dirname, 'menus-config.json');
    const allMenuItems = await transformMenuConfig(configPath);
    const menuItemsWithEmit = filterWithEmit(allMenuItems);
    
    console.log(`📊 加载完成: ${allMenuItems.length} 个菜单项，${menuItemsWithEmit.length} 个有emit动作`);

    // 只选择前3个菜单进行分析（避免过长分析）
    const selectedMenus = menuItemsWithEmit.slice(0, 3);

    // 创建分析配置
    const config = createDefaultConfig();
    config.llm = {
      ...config.llm,
      provider: 'deepseek',
      apiKey: process.env.DEEPSEEK_API_KEY || 'your-deepseek-api-key-here',
      model: 'deepseek-chat',
      baseUrl: 'https://api.deepseek.com',
      temperature: 0.3
    };

    // 配置爬虫参数（MenuCrawler需要MenuConfig类型的配置）
    config.crawler = {
      // CrawlerConfig 必需字段
      concurrency: 1,
      delay: 2000,
      retries: 2,
      timeout: 30000,
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      viewport: { width: 1920, height: 1080 },
      
      // MenuConfig 额外字段（通过 as any 传递）
      baseUrl: process.env.BASE_URL || 'http://localhost:3000/dashboard',
      loginConfig: {
        loginUrl: process.env.LOGIN_URL || 'http://localhost:3000/login',
        usernameSelector: process.env.USERNAME_SELECTOR || '#username',
        passwordSelector: process.env.PASSWORD_SELECTOR || '#password',
        submitSelector: process.env.LOGIN_BUTTON_SELECTOR || 'button[type="submit"]',
        username: process.env.LOGIN_USERNAME || 'admin',
        password: process.env.LOGIN_PASSWORD || 'password',
        successSelector: process.env.SUCCESS_INDICATOR || '.dashboard'
      }
    } as any;

    // 配置函数式导航回调
    config.onMenuOpen = async (emit: string[]): Promise<void> => {
      const currentMenuItem = (globalThis as any).currentAnalyzingMenuItem;
      if (currentMenuItem) {
        await handleMenuOpen(emit, currentMenuItem);
        return;
      }
      console.log(`  ⚠️ 未找到当前分析的菜单项`);
    };

    // 创建分析引擎
    const engine = new MenuAnalysisEngine(config);
    
    console.log(`🚀 开始分析 ${selectedMenus.length} 个菜单功能...\n`);
    
    // MenuAnalysisEngine 会自动处理登录和初始化
    console.log('🔐 MenuAnalysisEngine 将自动处理登录流程...');
    
    console.log('📋 第三步：开始菜单功能分析...');
    console.log('='.repeat(50));
    
    const results: MenuFunctionality[] = [];
    
    for (const menuItem of selectedMenus) {
      console.log(`🔸 分析菜单: ${menuItem.text}`);
      console.log(`   ID: ${menuItem.id}`);
      console.log(`   Emit: [${menuItem.emit?.join(', ') || 'none'}]`);
      
      // MenuAnalysisEngine 会自动处理登录状态检查
      
      try {
        // 设置当前菜单项供回调使用
        (globalThis as any).currentAnalyzingMenuItem = menuItem;
        
        console.log(`   🔄 开始页面分析...`);
        
        // 直接传入完整的 menuItem，引擎会自动处理登录和导航
        const functionality = await engine.analyzeSingleMenu(menuItem);
        
        results.push(functionality);
        console.log(`   ✅ 分析完成: ${functionality.primaryFunction}`);
        console.log(`   📊 置信度: ${(functionality.confidence * 100).toFixed(1)}%`);
        console.log(`   🔗 业务范围: ${functionality.businessScope}\n`);
        
      } catch (error) {
        console.log(`   ❌ 分析失败: ${error.message}`);
        
        // 提供错误提示
        if (error.message.includes('login') || error.message.includes('auth')) {
          console.log(`   💡 提示: 检查 config.crawler.loginConfig 配置\n`);
        } else {
          console.log(`   💡 提示: 检查页面结构或网络连接\n`);
        }
      }
    }
    
    // 清理
    delete (globalThis as any).currentAnalyzingMenuItem;
    
    console.log('='.repeat(50));
    console.log(`🎉 分析完成！成功分析了 ${results.length} 个菜单功能`);
    console.log(`📊 分析成功率: ${((results.length / selectedMenus.length) * 100).toFixed(1)}%`);
    
    console.log('\n📋 详细结果摘要:');
    results.forEach((result, index) => {
      console.log(`${index + 1}. ${result.menuName}: ${result.primaryFunction}`);
      console.log(`   置信度: ${(result.confidence * 100).toFixed(1)}%`);
      console.log(`   业务范围: ${result.businessScope}`);
      console.log(`   主要能力: ${result.capabilities.slice(0, 3).join(', ')}${result.capabilities.length > 3 ? '...' : ''}`);
    });
    
    // 提供使用建议
    console.log('\n💡 使用建议:');
    console.log('- 设置正确的登录配置以分析更多需要权限的菜单');
    console.log('- 检查以下环境变量:');
    console.log('  * LOGIN_URL, LOGIN_USERNAME, LOGIN_PASSWORD');
    console.log('  * BASE_URL, USERNAME_SELECTOR, PASSWORD_SELECTOR');
    console.log('  * LOGIN_BUTTON_SELECTOR, SUCCESS_INDICATOR');

    return results;

  } catch (error) {
    console.error('❌ 完整分析失败:', error);
    throw error;
  }
}

// 如果直接运行此文件
if (import.meta.url === `file://${process.argv[1]}`) {
  // 直接运行完整分析
  analyzeFullMenuTree().catch(console.error);
}

export { 
  analyzeFullMenuTree,
  handleMenuOpen,
  transformMenuConfig 
};