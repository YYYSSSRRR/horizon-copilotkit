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
import fs from 'fs';

// Load .env file from the project root
dotenv.config({ path: path.join(__dirname, '..', '.env') });

// 使用 TypeScript 导入
import { 
  createDefaultConfig,
  MenuAnalysisEngine,
  AnalysisConfig,
  MenuItem,
  PageAnalysis
} from '../src';
import { SimpleTransformer } from '../src/menu-transformers';

// 使用 TypeScript 类型
interface RawMenuItem {
  name?: string;
  href?: string;
  emit?: string[];
  subs?: Record<string, RawMenuItem>;
  actions?: Record<string, RawMenuItem>;
}

// 现在使用 SimpleTransformer
function transformMenuConfig(filePath: string): MenuItem[] {
  return SimpleTransformer.transformFromJsonFile(filePath);
}

function filterWithEmit(menuItems: MenuItem[]): MenuItem[] {
  return SimpleTransformer.filterWithEmit(menuItems);
}

/**
 * 菜单打开回调函数 - 这是核心的函数式导航实现
 */
async function handleMenuOpen(emit: string[], menuItem: MenuItem): Promise<PageAnalysis> {
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
        // 在实际应用中，这里调用你的页面导航函数
        // await yourNavigationSystem.navigateTo(actionData.Href);
        
      } else if (actionData.Action) {
        console.log(`      ⚡ 执行业务动作: ${actionData.Action}`);
        // 在实际应用中，这里调用你的动作执行函数
        // await yourActionSystem.execute(actionData.Action);
        
      } else if (actionData.CmdId) {
        console.log(`      🖥️ 执行系统命令: ${actionData.CmdId}`);
        // 在实际应用中，这里调用你的命令执行函数
        // await yourCommandSystem.execute(actionData.CmdId);
        
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
  
  // 返回模拟的页面分析结果
  return {
    url: menuItem.url || `function://emit-action-${menuItem.id}`,
    title: `${menuItem.text} - 功能页面`,
    content: {
      forms: [],
      buttons: [`${menuItem.text}操作按钮`, '确认', '取消'],
      links: [`返回${menuItem.parentId || '主页'}`, '帮助'],
      tables: [],
      images: [],
      metadata: {
        pageType: 'function-page',
        breadcrumbs: [menuItem.parentId || '主页', menuItem.text]
      }
    },
    functionality: {
      primaryFunction: `${menuItem.text}功能页面`,
      capabilities: [`执行${menuItem.text}相关操作`, '数据查询', '结果展示'],
      businessScope: `${menuItem.text}业务领域`,
      confidence: 0.95
    }
  };
}

/**
 * 完整的菜单分析流程（使用函数式导航）
 */
async function analyzeFunctionBasedMenus(): Promise<any[]> {
  try {
    console.log('🚀 开始函数式菜单导航分析...');

    // 第一步：加载和转换菜单配置
    console.log('\n📁 第一步：加载菜单配置...');
    const configPath = path.join(__dirname, 'menus-config.json');
    const allMenuItems = transformMenuConfig(configPath);
    const menuItemsWithEmit = filterWithEmit(allMenuItems);
    
    console.log(`✅ 配置加载完成`);
    console.log(`   总菜单项: ${allMenuItems.length} 个`);
    console.log(`   有emit动作: ${menuItemsWithEmit.length} 个`);
    console.log(`   选择分析: ${Math.min(6, menuItemsWithEmit.length)} 个\n`);

    // 第二步：创建分析配置
    console.log('⚙️ 第二步：创建分析配置...');
    const config = createDefaultConfig();
    
    // 配置 LLM（使用 DeepSeek）
    config.llm = {
      ...config.llm,
      provider: 'deepseek',
      apiKey: process.env.DEEPSEEK_API_KEY || 'your-deepseek-api-key-here',
      model: 'deepseek-chat',
      baseUrl: 'https://api.deepseek.com',
      temperature: 0.3,
      systemPrompt: `
你是一个专业的企业级菜单功能分析师。请分析页面内容并生成中文的菜单功能描述。

请严格按照以下JSON格式返回分析结果：
{
  "menuId": "菜单ID",
  "menuName": "菜单名称", 
  "menuPath": "菜单路径",
  "url": "页面URL",
  "primaryFunction": "主要功能描述（一句话概括）",
  "capabilities": ["功能能力列表"],
  "businessScope": "业务范围描述",
  "userActions": ["用户可执行的操作列表"],
  "dataManagement": {
    "dataTypes": ["涉及的数据类型"],
    "operations": ["支持的数据操作"], 
    "integrations": ["相关系统集成"]
  },
  "technicalDetails": {
    "componentTypes": ["页面组件类型"],
    "frameworks": ["使用的框架"],
    "apis": ["API接口"]
  },
  "usageScenarios": ["使用场景描述"],
  "relatedModules": ["相关模块"],
  "confidence": 0.9
}
      `.trim()
    };

    // 配置输出
    config.output = {
      format: 'json',
      outputPath: './examples/results/function-based-analysis',
      includeScreenshots: false,
      includeRawContent: false
    };

    // 配置爬虫参数（针对函数式导航优化）
    config.crawler = {
      concurrency: 1,  // 串行处理，避免并发问题
      delay: 2000,     // 适当延迟
      retries: 2,
      timeout: 30000,
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    };

    // 关键：添加函数式菜单打开回调
    config.onMenuOpen = async (emit) => {
      // 这里需要额外的上下文信息，但为了演示我们使用简化版本
      const menuItem = { text: '演示菜单', id: 'demo-menu' };
      return await handleMenuOpen(emit, menuItem);
    };

    console.log('✅ 配置创建完成\n');

    // 第三步：演示菜单转换和函数式导航
    console.log('🔍 第三步：演示函数式导航...');
    console.log('=====================================');
    
    const selectedItems = menuItemsWithEmit.slice(0, 3);
    const analysisResults = [];

    for (const menuItem of selectedItems) {
      console.log(`🔸 分析菜单: ${menuItem.text}`);
      console.log(`   ID: ${menuItem.id}`);
      console.log(`   层级: ${menuItem.level}, 父菜单: ${menuItem.parentId || '(root)'}`);
      
      if (menuItem.emit && menuItem.emit.length > 0) {
        // 调用函数式导航
        const pageAnalysis = await handleMenuOpen(menuItem.emit, menuItem);
        analysisResults.push({
          menuItem,
          pageAnalysis,
          timestamp: new Date().toISOString()
        });
      } else {
        console.log('   ⚠️ 该菜单没有emit动作，跳过\n');
      }
    }

    // 第四步：生成分析报告
    console.log('📊 第四步：生成分析报告...');
    console.log('=====================================');
    
    console.log(`✅ 分析完成！处理了 ${analysisResults.length} 个菜单功能\n`);
    
    console.log('📋 菜单功能摘要:');
    analysisResults.forEach((result, index) => {
      const { menuItem, pageAnalysis } = result;
      console.log(`${index + 1}. ${menuItem.text}: ${pageAnalysis.functionality.primaryFunction}`);
      console.log(`   URL: ${pageAnalysis.url}`);
      console.log(`   能力: ${pageAnalysis.functionality.capabilities.join(', ')}`);
      console.log(`   置信度: ${(pageAnalysis.functionality.confidence * 100).toFixed(1)}%`);
      console.log(`   页面元素: ${pageAnalysis.content.buttons.length}个按钮, ${pageAnalysis.content.links.length}个链接\n`);
    });

    // 第五步：保存结果
    console.log('💾 第五步：保存分析结果...');
    const resultsDir = path.join(__dirname, 'results');
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true });
    }
    
    const outputFile = path.join(resultsDir, 'function-based-analysis.json');
    fs.writeFileSync(outputFile, JSON.stringify({
      metadata: {
        analysisType: 'function-based-navigation',
        timestamp: new Date().toISOString(),
        totalMenus: allMenuItems.length,
        analyzedMenus: analysisResults.length,
        withEmit: menuItemsWithEmit.length
      },
      results: analysisResults
    }, null, 2));
    
    console.log(`✅ 结果已保存到: ${outputFile}\n`);

    // 使用说明
    console.log('📝 实际使用方式:');
    console.log('=====================================');
    console.log('1. 菜单转换:');
    console.log('   const menuItems = SimpleTransformer.transformFromJsonFile("./menus-config.json");');
    console.log('');
    console.log('2. 配置分析引擎:');
    console.log('   const config = {');
    console.log('     onMenuOpen: async (emit) => { return await handleMenuOpen(emit, menuItem); }');
    console.log('   };');
    console.log('');
    console.log('3. 进行分析:');
    console.log('   const engine = new MenuAnalysisEngine(config);');
    console.log('   const functionalities = await engine.analyze();');
    console.log('');
    console.log('🎯 核心优势:');
    console.log('- 📱 支持函数调用打开页面，不依赖URL');
    console.log('- 🔧 保持完整的页面内容分析功能');
    console.log('- 🚀 完美适配SPA和企业级应用');
    console.log('- ⚡ 支持复杂的业务动作执行');

    return analysisResults;

  } catch (error) {
    console.error('❌ 分析失败:', error);
    
    // 提供故障排除建议
    if (error.message.includes('API key')) {
      console.error('💡 请设置正确的 DEEPSEEK_API_KEY 环境变量');
    }
    if (error.message.includes('ENOENT') && error.message.includes('menus-config.json')) {
      console.error('💡 请确保 examples/menus-config.json 文件存在');
    }
    
    throw error;
  }
}

/**
 * 单独分析某个菜单项的示例
 */
async function analyzeSingleFunctionMenu(): Promise<PageAnalysis> {
  try {
    console.log('🎯 单个函数式菜单分析示例...');

    // 模拟一个菜单项
    const menuItem = {
      id: 'dcc-view',
      text: 'DCC视图',
      level: 3,
      parentId: 'u2020-f-tp-view',
      hasSubmenu: false,
      emit: ['jumpSPAPage', "{'Action': 'com.huawei.te.dccmgr.DoDcnViewAction'}"]
    };

    console.log(`📋 分析菜单: ${menuItem.text}`);
    
    // 执行函数式导航和分析
    const pageAnalysis = await handleMenuOpen(menuItem.emit, menuItem);
    
    console.log('✅ 单菜单分析完成!');
    console.log('📄 页面功能:', pageAnalysis.functionality.primaryFunction);
    console.log('🎯 主要能力:', pageAnalysis.functionality.capabilities.join(', '));
    console.log('🏗️ 页面组件:', `${pageAnalysis.content.buttons.length}个按钮, ${pageAnalysis.content.links.length}个链接`);

    return pageAnalysis;

  } catch (error) {
    console.error('❌ 单菜单分析失败:', error);
    throw error;
  }
}

// 如果直接运行此文件
if (import.meta.url === `file://${process.argv[1]}`) {
  // 检查是否设置了环境变量
  if (!process.env.DEEPSEEK_API_KEY) {
    console.log('⚠️  建议设置 DEEPSEEK_API_KEY 环境变量以启用完整功能');
    console.log('   export DEEPSEEK_API_KEY=your-deepseek-api-key');
    console.log('   （不设置也可以运行演示，但无法调用LLM分析）');
    console.log('');
  }

  // 可以选择运行完整分析或单菜单分析
  const analysisType = process.argv[2] || 'full';
  
  if (analysisType === 'single') {
    analyzeSingleFunctionMenu().catch(console.error);
  } else {
    analyzeFunctionBasedMenus().catch(console.error);
  }
}

export { 
  analyzeFunctionBasedMenus, 
  analyzeSingleFunctionMenu,
  handleMenuOpen,
  transformMenuConfig 
};