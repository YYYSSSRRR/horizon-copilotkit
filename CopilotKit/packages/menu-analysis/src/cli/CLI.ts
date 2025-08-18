import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { MenuAnalysisEngine } from '../core/MenuAnalysisEngine';
import { createDefaultConfig, createMenuConfig, validateConfig, loadConfigFromEnv, mergeConfigs } from '../config/ConfigManager';
import { AnalysisConfig } from '../types';
import * as fs from 'fs-extra';
import * as path from 'path';

export async function runCLI(): Promise<void> {
  const argv = await yargs(hideBin(process.argv))
    .command(
      'analyze',
      'Analyze menu functionality for a website',
      (yargs) => {
        return yargs
          .option('url', {
            alias: 'u',
            type: 'string',
            description: 'Base URL of the website to analyze',
            demandOption: true
          })
          .option('config', {
            alias: 'c',
            type: 'string',
            description: 'Path to configuration file'
          })
          .option('output', {
            alias: 'o',
            type: 'string',
            description: 'Output file path',
            default: './menu-analysis-results'
          })
          .option('format', {
            alias: 'f',
            type: 'string',
            description: 'Output format (only json supported)',
            default: 'json',
            hidden: true
          })
          .option('login-url', {
            type: 'string',
            description: 'Login page URL if authentication is required'
          })
          .option('username', {
            type: 'string',
            description: 'Username for login'
          })
          .option('password', {
            type: 'string',
            description: 'Password for login'
          })
          .option('username-selector', {
            type: 'string',
            description: 'CSS selector for username field',
            default: 'input[name="username"], input[type="email"]'
          })
          .option('password-selector', {
            type: 'string',
            description: 'CSS selector for password field',
            default: 'input[name="password"], input[type="password"]'
          })
          .option('submit-selector', {
            type: 'string',
            description: 'CSS selector for login submit button',
            default: 'button[type="submit"], input[type="submit"]'
          })
          .option('menu-selectors', {
            type: 'string',
            description: 'Comma-separated list of CSS selectors for menu items'
          })
          .option('exclude-patterns', {
            type: 'string',
            description: 'Comma-separated list of patterns to exclude'
          })
          .option('max-depth', {
            type: 'number',
            description: 'Maximum menu depth to crawl',
            default: 3
          })
          .option('concurrency', {
            type: 'number',
            description: 'Number of concurrent page analyses',
            default: 3
          })
          .option('delay', {
            type: 'number',
            description: 'Delay between requests in milliseconds',
            default: 1000
          })
          .option('llm-model', {
            type: 'string',
            description: 'LLM model to use',
            default: 'gpt-3.5-turbo'
          })
          .option('verbose', {
            alias: 'v',
            type: 'boolean',
            description: 'Enable verbose logging',
            default: false
          });
      },
      async (argv) => {
        await handleAnalyzeCommand(argv);
      }
    )
    .command(
      'single',
      'Analyze a single menu page',
      (yargs) => {
        return yargs
          .option('url', {
            alias: 'u',
            type: 'string',
            description: 'URL of the page to analyze',
            demandOption: true
          })
          .option('name', {
            alias: 'n',
            type: 'string',
            description: 'Name of the menu/page',
            demandOption: true
          })
          .option('output', {
            alias: 'o',
            type: 'string',
            description: 'Output file path',
            default: './single-menu-analysis.json'
          });
      },
      async (argv) => {
        await handleSingleCommand(argv);
      }
    )
    .command(
      'config',
      'Generate a configuration file template',
      (yargs) => {
        return yargs
          .option('output', {
            alias: 'o',
            type: 'string',
            description: 'Output path for config file',
            default: './menu-analysis.config.json'
          });
      },
      async (argv) => {
        await handleConfigCommand(argv);
      }
    )
    .demandCommand(1, 'You need at least one command before moving on')
    .help()
    .alias('help', 'h')
    .parse();
}

async function handleAnalyzeCommand(argv: any): Promise<void> {
  try {
    console.log('🔍 Starting menu analysis...');
    
    // Load configuration
    let config = createDefaultConfig();
    
    // Load from environment variables
    const envConfig = loadConfigFromEnv();
    config = mergeConfigs(config, envConfig);
    
    // Load from config file if provided
    if (argv.config) {
      const fileConfig = await loadConfigFromFile(argv.config);
      config = mergeConfigs(config, fileConfig);
    }
    
    // Apply command line arguments
    const cliConfig = buildConfigFromCLI(argv);
    config = mergeConfigs(config, cliConfig);
    
    // Validate configuration
    validateConfig(config);
    
    // Create menu config
    const menuConfig = createMenuConfig(argv.url);
    
    // Apply menu-specific CLI options
    if (argv.menuSelectors) {
      menuConfig.menuSelectors = argv.menuSelectors.split(',').map((s: string) => s.trim());
    }
    if (argv.excludePatterns) {
      menuConfig.excludePatterns = argv.excludePatterns.split(',').map((s: string) => s.trim());
    }
    menuConfig.maxDepth = argv.maxDepth;
    
    // Add login configuration if provided
    if (argv.loginUrl && argv.username && argv.password) {
      menuConfig.loginConfig = {
        loginUrl: argv.loginUrl,
        usernameSelector: argv.usernameSelector,
        passwordSelector: argv.passwordSelector,
        submitSelector: argv.submitSelector,
        username: argv.username,
        password: argv.password
      };
    }
    
    // Create analysis engine
    const engine = new MenuAnalysisEngine({
      ...config,
      crawler: {
        ...config.crawler,
        ...menuConfig
      }
    });
    
    // Run analysis
    const results = await engine.analyze();
    
    console.log(`✅ Analysis completed! Found ${results.length} menu functionalities.`);
    console.log(`📄 Results saved to: ${config.output.outputPath}`);
    
  } catch (error) {
    console.error('❌ Analysis failed:', error);
    process.exit(1);
  }
}

async function handleSingleCommand(argv: any): Promise<void> {
  try {
    console.log(`🔍 Analyzing single page: ${argv.name}`);
    
    const config = createDefaultConfig();
    const envConfig = loadConfigFromEnv();
    const mergedConfig = mergeConfigs(config, envConfig);
    
    // Override output path
    mergedConfig.output.outputPath = argv.output;
    
    validateConfig(mergedConfig);
    
    const menuConfig = createMenuConfig(argv.url);
    const engine = new MenuAnalysisEngine({
      ...mergedConfig,
      crawler: {
        ...mergedConfig.crawler,
        ...menuConfig
      }
    });
    
    const result = await engine.analyzeSingleMenu(argv.url, argv.name);
    
    // Save result
    await fs.writeJson(argv.output, result, { spaces: 2 });
    
    console.log(`✅ Single page analysis completed!`);
    console.log(`📄 Result saved to: ${argv.output}`);
    
  } catch (error) {
    console.error('❌ Analysis failed:', error);
    process.exit(1);
  }
}

async function handleConfigCommand(argv: any): Promise<void> {
  try {
    const defaultConfig = createDefaultConfig();
    const sampleMenuConfig = createMenuConfig('https://example.com');
    
    const configTemplate = {
      ...defaultConfig,
      menu: sampleMenuConfig,
      examples: {
        'Basic usage': {
          baseUrl: 'https://your-website.com',
          menuSelectors: [
            '[role="navigation"] a',
            '.menu a',
            '.nav a'
          ],
          excludePatterns: ['logout', 'help'],
          maxDepth: 3
        },
        'With login': {
          baseUrl: 'https://admin.your-website.com',
          loginConfig: {
            loginUrl: 'https://admin.your-website.com/login',
            usernameSelector: 'input[name="username"]',
            passwordSelector: 'input[name="password"]',
            submitSelector: 'button[type="submit"]',
            username: 'your-username',
            password: 'your-password'
          }
        }
      }
    };
    
    await fs.writeJson(argv.output, configTemplate, { spaces: 2 });
    
    console.log(`✅ Configuration template created at: ${argv.output}`);
    console.log('📝 Edit the file to customize your analysis settings.');
    
  } catch (error) {
    console.error('❌ Failed to create config file:', error);
    process.exit(1);
  }
}

async function loadConfigFromFile(configPath: string): Promise<Partial<AnalysisConfig>> {
  try {
    if (!await fs.pathExists(configPath)) {
      throw new Error(`Config file not found: ${configPath}`);
    }
    
    const config = await fs.readJson(configPath);
    return config;
    
  } catch (error) {
    throw new Error(`Failed to load config file: ${error}`);
  }
}

function buildConfigFromCLI(argv: any): Partial<AnalysisConfig> {
  const config: Partial<AnalysisConfig> = {};
  
  if (argv.output) {
    config.output = {
      format: 'json',
      outputPath: argv.output
    };
  }
  
  if (argv.concurrency || argv.delay) {
    config.crawler = {};
    if (argv.concurrency) config.crawler.concurrency = argv.concurrency;
    if (argv.delay) config.crawler.delay = argv.delay;
  }
  
  if (argv.llmModel) {
    config.llm = {
      model: argv.llmModel
    };
  }
  
  return config;
}