/**
 * 分析 coloringbook.ai 网站菜单的示例
 */

// Import polyfills first
import '../polyfills.js';

// Load environment variables from .env file
import dotenv from 'dotenv';
import path from 'path';

// Load .env file from the project root
dotenv.config({ path: path.join(__dirname, '..', '.env') });

import { 
  MenuAnalysisEngine, 
  createDefaultConfig, 
  createMenuConfig,
  mergeConfigs
} from '../src';

async function analyzeColoringBook() {
  try {
    console.log('🎨 开始分析 coloringbook.ai 网站菜单...');

    // 创建基础配置
    const config = createDefaultConfig();
    
    // 配置 DeepSeek LLM（需要设置你的 API Key）
    config.llm = {
      ...config.llm,
      provider: 'deepseek',
      apiKey: process.env.DEEPSEEK_API_KEY || 'your-deepseek-api-key-here',
      model: 'deepseek-chat',
      baseUrl: 'https://api.deepseek.com',
      temperature: 0.3,
      systemPrompt: `
你是一个专业的网站菜单功能分析师。请分析网页内容并生成中文的菜单功能描述。

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
      outputPath: './examples/results/coloringbook-analysis',
      includeScreenshots: false,
      includeRawContent: false
    };

    // 配置爬虫参数
    config.crawler = {
      concurrency: 1, // 降低到1个并发，完全避免并发请求
      delay: 5000,    // 增加到5秒延迟
      retries: 2,     // 减少重试次数
      timeout: 45000, // 增加超时时间
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      viewport: { width: 1920, height: 1080 }
    };

    // 创建菜单配置
    const menuConfig = createMenuConfig('https://www.coloringbook.ai/zh');
    
    // 针对 coloringbook.ai 网站的菜单选择器
    menuConfig.menuSelectors = [
      // 常见的导航菜单选择器
      'nav a',
      '.navbar a',
      '.navigation a',
      '.menu a',
      '.header a',
      '[role="navigation"] a',
      // 可能的侧边栏或其他菜单
      '.sidebar a',
      '.side-nav a',
      '.main-nav a',
      // 页脚链接
      'footer a',
      // 按钮样式的链接
      '.btn[href]',
      'button[onclick*="location"]',
      // 特定于AI工具网站的可能选择器
      '.tool-nav a',
      '.feature-nav a',
      '.product-nav a'
    ];

    // 排除一些不需要分析的链接
    menuConfig.excludePatterns = [
      'mailto:',
      'tel:',
      'javascript:',
      '#',
      'facebook.com',
      'twitter.com',
      'instagram.com',
      'linkedin.com',
      'youtube.com',
      'privacy',
      'terms',
      'contact',
      'about-us'
    ];

    menuConfig.maxDepth = 2; // 限制深度，避免过度爬取
    menuConfig.waitTimeout = 45000; // 较长的等待时间

    // 合并配置
    const finalConfig = mergeConfigs(config, {
      crawler: {
        ...config.crawler,
        ...menuConfig
      }
    });

    // 创建分析引擎
    const engine = new MenuAnalysisEngine(finalConfig);
    
    // 运行分析
    console.log('🔍 开始发现菜单结构...');
    const results = await engine.analyze();

    console.log(`✅ 分析完成！`);
    console.log(`📊 发现 ${results.length} 个菜单功能`);
    console.log(`📁 结果保存到: ${finalConfig.output.outputPath}`);

    // 显示分析摘要
    console.log('\n📋 菜单功能摘要:');
    results.forEach((result, index) => {
      console.log(`${index + 1}. ${result.menuName}: ${result.primaryFunction}`);
      console.log(`   URL: ${result.url}`);
      console.log(`   能力: ${result.capabilities.join(', ')}`);
      console.log(`   置信度: ${(result.confidence * 100).toFixed(1)}%\n`);
    });

    // 按功能类型分组
    const groupedByFunction = results.reduce((acc: any, result) => {
      const category = result.primaryFunction;
      if (!acc[category]) acc[category] = [];
      acc[category].push(result);
      return acc;
    }, {});

    console.log('🗂️ 按功能分类:');
    Object.entries(groupedByFunction).forEach(([category, items]) => {
      const itemList = items as any[];
      console.log(`\n${category} (${itemList.length}个):`);
      itemList.forEach(item => console.log(`  - ${item.menuName}`));
    });

    return results;

  } catch (error) {
    console.error('❌ 分析失败:', error);
    
    // 提供一些故障排除建议
    if (error.message.includes('API key')) {
      console.error('💡 请设置正确的 OPENAI_API_KEY 环境变量');
    }
    if (error.message.includes('timeout')) {
      console.error('💡 网站响应较慢，可以尝试增加 timeout 设置');
    }
    if (error.message.includes('找不到元素')) {
      console.error('💡 可能需要调整菜单选择器，网站结构可能有变化');
    }
    
    throw error;
  }
}

// 单独分析主页的示例
async function analyzeSinglePage() {
  try {
    console.log('🎯 分析单个页面: coloringbook.ai 主页');

    const config = createDefaultConfig();
    config.llm.apiKey = process.env.DEEPSEEK_API_KEY || 'your-deepseek-api-key-here';
    config.output.outputPath = path.join(__dirname, '..', 'examples', 'results', 'coloringbook-homepage.json');

    const menuConfig = createMenuConfig('https://www.coloringbook.ai/zh');
    const finalConfig = mergeConfigs(config, {
      crawler: {
        ...config.crawler,
        ...menuConfig
      }
    });

    const engine = new MenuAnalysisEngine(finalConfig);
    const result = await engine.analyzeSingleMenu(
      'https://www.coloringbook.ai/zh', 
      'ColoringBook AI 主页'
    );

    // 手动保存结果到文件
    const fs = require('fs-extra');
    await fs.ensureDir(path.dirname(finalConfig.output.outputPath));
    await fs.writeJson(finalConfig.output.outputPath, result, { spaces: 2 });

    console.log('✅ 单页分析完成!');
    console.log('📄 页面功能:', result.primaryFunction);
    console.log('🎯 主要能力:', result.capabilities.join(', '));
    console.log('📁 结果保存到:', finalConfig.output.outputPath);

    return result;

  } catch (error) {
    console.error('❌ 单页分析失败:', error);
    throw error;
  }
}

// 如果直接运行此文件
if (require.main === module) {
  // 检查是否设置了环境变量
  if (!process.env.DEEPSEEK_API_KEY) {
    console.log('⚠️  请先设置 DEEPSEEK_API_KEY 环境变量');
    console.log('   export DEEPSEEK_API_KEY=your-deepseek-api-key');
    console.log('   或者在代码中直接设置 apiKey');
    console.log('');
  }

  // 可以选择运行完整分析或单页分析
  const analysisType = process.argv[2] || 'full';
  
  if (analysisType === 'single') {
    analyzeSinglePage();
  } else {
    analyzeColoringBook();
  }
}

export { analyzeColoringBook, analyzeSinglePage };