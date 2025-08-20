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
} from '../src/index.js';
import { SimpleTransformer } from '../src/menu-transformers/index.js';
import { Page } from 'playwright';

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
async function handleMenuOpen(page: Page, emit: string[], menuItem: MenuItem): Promise<void> {
  console.log(`📱 通过函数打开菜单: ${menuItem.text}`);
  console.log(`   Emit 动作: [${emit.map(e => `"${e}"`).join(', ')}]`);
  console.log(`   新窗口模式: ${menuItem.preferNewWindow ? '是' : '否'}`);

  try {
    // 先初始化，再执行跳转，预期会有导航发生
    await page.evaluate(({ emit }) => {
      console.log('into page.evaluate...');
      // 初始化 PIU
      if (!(window as any).isInitPIU) {
        (window as any).Prel.define({ 'abc@1.0.0': { config: { base: '/invgrpwebsite' } } });
        (window as any).Prel.start('abc', '1.0.0', [], (piu, st) => {
          (window as any).abcPiu = piu;
          // 执行跳转（这会导致页面跳转和上下文销毁）
          (window as any).abcPiu.emit('userAction', ...emit);
        });
        (window as any).isInitPIU = true;
      } else {
        // 执行跳转（这会导致页面跳转和上下文销毁）
        (window as any).abcPiu.emit('userAction', ...emit);
      }
    }, { emit });

  } catch (e) {
    // 预期的错误 - 执行上下文被销毁意味着跳转成功
    if (e.message.includes('Execution context was destroyed')) {
      console.log(`   🔄 页面正在跳转...`);
    } else {
      console.error('意外错误：', e);
    }
  }

  // 增加3秒等待，给页面跳转更充足的时间
  console.log(`   ⏰ 等待3秒...`);
  await page.waitForTimeout(3000);

  // 等待新页面加载完成
  console.log(`   ⏳ 等待新页面加载...`);
  try {
    await page.waitForLoadState('networkidle', { timeout: 10000 });
    console.log(`   ✅ 页面加载完成: ${page.url()}\n`);
  } catch (e) {
    console.log(`   ⚠️  页面加载超时，当前页面: ${page.url()}\n`);
  }
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

    const selectedMenus = menuItemsWithEmit;

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
        password: process.env.LOGIN_PASSWORD || 'password'
      }
    } as any;

    // 配置函数式导航回调
    config.onMenuOpen = async (page: Page, emit: string[]): Promise<void> => {
      const currentMenuItem = (globalThis as any).currentAnalyzingMenuItem;
      if (currentMenuItem) {
        await handleMenuOpen(page, emit, currentMenuItem);
        return;
      }
      console.log(`  ⚠️ 未找到当前分析的菜单项`);
    };

    // 配置自定义内容提取回调
    (config as any).onExtractContent = async (page: Page, menuItem: any) => {
      let windowContent: any = { html: '', title: '', url: '' };

      if (menuItem.preferNewWindow) {
        await page.waitForSelector('iframe.spa_iframe');

        // Extract page content from spa iframe
        windowContent = await page.evaluate(() => {
          const spaIframes = document.querySelectorAll('iframe.spa_iframe');
          const lastSpaIframe = spaIframes[spaIframes.length - 1] as HTMLIFrameElement;

          if (lastSpaIframe && lastSpaIframe.contentDocument) {
            return {
              title: lastSpaIframe.contentDocument.title,
              html: lastSpaIframe.contentDocument.documentElement.outerHTML,
              url: lastSpaIframe.contentWindow?.location.href || ''
            };
          }

          return { title: '', html: '', url: '' };
        });
      } else {
        // Extract page content
        await page.waitForSelector('#webswing-root-container iframe');

        windowContent = await page.evaluate(() => {
          const container = document.querySelector('#webswing-root-container');
          const iframes = container?.querySelectorAll('iframe');
          const lastIframe = iframes?.[iframes.length - 1] as HTMLIFrameElement;

          if (lastIframe && lastIframe.contentDocument) {
            return {
              title: lastIframe.contentDocument.title,
              html: lastIframe.contentDocument.documentElement.outerHTML,
              url: lastIframe.contentWindow?.location.href || ''
            };
          }

          return { title: '', html: '', url: '' };
        });
      }

      return windowContent;
    };

    // 创建分析引擎
    const engine = new MenuAnalysisEngine(config);

    console.log(`🚀 开始分析 ${selectedMenus.length} 个菜单功能...\n`);

    try {

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

      // 保存结果到文件
      const fs = require('fs-extra');
      const outputPath = path.join(__dirname, 'results', 'NCE-analysis.json');
      await fs.ensureDir(path.dirname(outputPath));
      await fs.writeJson(outputPath, results, { spaces: 2 });

      console.log(`📁 结果保存到: ${outputPath}`);

      return results;

    } catch (analysisError) {
      console.error('❌ 菜单分析过程失败:', analysisError);
      throw analysisError;
    } finally {
      // 确保清理引擎资源
      try {
        await engine.close();
        console.log('🧹 引擎资源已清理');
      } catch (cleanupError) {
        console.log('⚠️ 清理资源时出现警告:', cleanupError.message);
      }
    }

  } catch (error) {
    console.error('❌ 完整分析失败:', error);
    throw error;
  }
}

analyzeFullMenuTree().catch(console.error);
