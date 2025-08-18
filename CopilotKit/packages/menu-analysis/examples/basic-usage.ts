/**
 * Basic usage example for @copilotkit/menu-analysis
 */

import { 
  MenuAnalysisEngine, 
  createDefaultConfig, 
  createMenuConfig,
  mergeConfigs,
  validateConfig
} from '../src';

async function basicAnalysis() {
  try {
    console.log('🚀 Starting basic menu analysis...');

    // Create default configuration
    const defaultConfig = createDefaultConfig();
    
    // Customize configuration
    const customConfig = {
      llm: {
        ...defaultConfig.llm,
        apiKey: process.env.OPENAI_API_KEY || 'your-api-key-here',
        model: 'gpt-3.5-turbo',
        temperature: 0.3
      },
      output: {
        ...defaultConfig.output,
        format: 'json' as const,
        outputPath: './examples/results/basic-analysis'
      },
      crawler: {
        ...defaultConfig.crawler,
        concurrency: 2, // Lower concurrency for demo
        delay: 2000     // Longer delay to be respectful
      }
    };

    // Create menu configuration
    const menuConfig = createMenuConfig('https://example.com');
    menuConfig.menuSelectors = [
      'nav a',
      '.menu a',
      '.navigation a'
    ];
    menuConfig.excludePatterns = [
      'mailto:',
      'tel:',
      'javascript:',
      '#'
    ];
    menuConfig.maxDepth = 2;

    // Merge configurations
    const finalConfig = mergeConfigs(customConfig, {
      crawler: {
        ...customConfig.crawler,
        ...menuConfig
      }
    });

    // Validate configuration
    validateConfig(finalConfig);

    // Create and run analysis engine
    const engine = new MenuAnalysisEngine(finalConfig);
    const results = await engine.analyze();

    console.log(`✅ Analysis completed!`);
    console.log(`📊 Found ${results.length} menu functionalities`);
    console.log(`📁 Results saved to: ${finalConfig.output.outputPath}`);

    // Display summary
    console.log('\n📋 Summary:');
    results.forEach((result, index) => {
      console.log(`${index + 1}. ${result.menuName}: ${result.primaryFunction}`);
    });

  } catch (error) {
    console.error('❌ Analysis failed:', error);
    process.exit(1);
  }
}

// Run the example
if (require.main === module) {
  basicAnalysis();
}