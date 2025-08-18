/**
 * Example with authentication for private systems
 */

import { 
  MenuAnalysisEngine, 
  createDefaultConfig, 
  createMenuConfig,
  mergeConfigs
} from '../src';

async function authenticatedAnalysis() {
  try {
    console.log('🔐 Starting authenticated menu analysis...');

    // Create configuration with authentication
    const config = createDefaultConfig();
    config.llm.apiKey = process.env.OPENAI_API_KEY || 'your-api-key-here';
    config.output.outputPath = './examples/results/admin-analysis';
    config.output.format = 'markdown';

    // Create menu configuration with login
    const menuConfig = createMenuConfig('https://admin.example.com');
    
    // Configure authentication
    menuConfig.loginConfig = {
      loginUrl: 'https://admin.example.com/login',
      usernameSelector: 'input[name="username"]',
      passwordSelector: 'input[name="password"]',
      submitSelector: 'button[type="submit"]',
      username: process.env.ADMIN_USERNAME || 'admin',
      password: process.env.ADMIN_PASSWORD || 'password',
      successSelector: '.dashboard, .admin-panel' // Optional: selector to confirm login success
    };

    // Configure menu selectors for admin interface
    menuConfig.menuSelectors = [
      '.admin-sidebar a',
      '.main-navigation a',
      '[role="navigation"] a',
      '.menu-item a'
    ];

    // Exclude common admin patterns
    menuConfig.excludePatterns = [
      'logout',
      'help',
      'support',
      'documentation',
      'profile',
      'settings/personal'
    ];

    menuConfig.maxDepth = 3;
    menuConfig.waitTimeout = 45000; // Longer timeout for admin pages

    const finalConfig = mergeConfigs(config, {
      crawler: {
        ...config.crawler,
        ...menuConfig,
        concurrency: 2, // Conservative for admin systems
        delay: 3000     // Respectful delay
      }
    });

    // Create and run analysis
    const engine = new MenuAnalysisEngine(finalConfig);
    const results = await engine.analyze();

    console.log(`✅ Authenticated analysis completed!`);
    console.log(`📊 Analyzed ${results.length} admin functionalities`);

    // Group results by top-level menu
    const grouped = results.reduce((acc: any, result) => {
      const topLevel = result.menuPath.split(' > ')[0] || 'Other';
      if (!acc[topLevel]) acc[topLevel] = [];
      acc[topLevel].push(result);
      return acc;
    }, {});

    console.log('\n📋 Admin Menu Structure:');
    Object.entries(grouped).forEach(([category, items]: [string, any[]]) => {
      console.log(`\n🗂️  ${category} (${items.length} items):`);
      items.forEach(item => {
        console.log(`   - ${item.menuName}: ${item.primaryFunction}`);
      });
    });

  } catch (error) {
    console.error('❌ Authenticated analysis failed:', error);
    
    // Provide helpful error messages
    if (error.message.includes('login')) {
      console.error('💡 Check your login credentials and selectors');
    }
    if (error.message.includes('timeout')) {
      console.error('💡 Try increasing the timeout or reducing concurrency');
    }
    
    process.exit(1);
  }
}

// Run the example
if (require.main === module) {
  authenticatedAnalysis();
}