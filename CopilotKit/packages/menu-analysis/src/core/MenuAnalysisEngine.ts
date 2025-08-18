import { MenuCrawler } from '../crawler/MenuCrawler';
import { PageAnalyzer } from '../analyzer/PageAnalyzer';
import { LLMAnalyzer } from '../llm/LLMAnalyzer';
import { OutputManager } from '../output/OutputManager';
import { Logger } from '../utils/Logger';
import { ProgressTracker } from '../utils/ProgressTracker';
import { 
  AnalysisConfig, 
  MenuItem, 
  PageAnalysis, 
  MenuFunctionality, 
  LLMAnalysisRequest 
} from '../types';

export class MenuAnalysisEngine {
  private config: AnalysisConfig;
  private logger: Logger;
  private progressTracker: ProgressTracker;
  private menuCrawler: MenuCrawler;
  private llmAnalyzer: LLMAnalyzer;
  private outputManager: OutputManager;

  constructor(config: AnalysisConfig) {
    this.config = config;
    this.logger = new Logger('info', 'menu-analysis.log');
    this.progressTracker = new ProgressTracker(this.logger);
    
    this.menuCrawler = new MenuCrawler(config.crawler as any, this.logger);
    this.llmAnalyzer = new LLMAnalyzer(config.llm, this.logger);
    this.outputManager = new OutputManager(config.output, this.logger);
  }

  async analyze(): Promise<MenuFunctionality[]> {
    try {
      this.logger.info('Starting menu analysis process...');

      // Step 1: Initialize browser and login
      await this.menuCrawler.initialize();
      await this.menuCrawler.login();

      // Step 2: Discover all menus
      this.logger.info('Discovering menu structure...');
      const menuItems = await this.menuCrawler.discoverMenus();
      this.logger.info(`Found ${menuItems.length} menu items`);

      // Step 3: Analyze each menu page
      this.logger.info('Starting page analysis...');
      const pageAnalyses = await this.analyzePages(menuItems);
      
      // Step 4: Generate functionality descriptions using LLM
      this.logger.info('Generating functionality descriptions...');
      const functionalities = await this.generateFunctionalities(menuItems, pageAnalyses);

      // Step 5: Save results
      this.logger.info('Saving analysis results...');
      await this.outputManager.saveResults(functionalities);

      this.logger.info(`Analysis completed! Processed ${functionalities.length} menus`);
      return functionalities;

    } catch (error) {
      this.logger.error('Analysis failed:', error);
      throw error;
    } finally {
      // Cleanup
      await this.menuCrawler.close();
    }
  }

  private async analyzePages(menuItems: MenuItem[]): Promise<Map<string, PageAnalysis>> {
    const pageAnalyses = new Map<string, PageAnalysis>();
    const page = await this.menuCrawler.getPage();
    // Pass the onMenuOpen callback to PageAnalyzer
    const pageAnalyzer = new PageAnalyzer(page, this.logger, this.config.onMenuOpen);

    this.progressTracker.start(menuItems.length, 'Analyzing pages');

    const concurrency = this.config.crawler.concurrency || 3;
    const delay = this.config.crawler.delay || 1000;

    for (let i = 0; i < menuItems.length; i += concurrency) {
      const batch = menuItems.slice(i, i + concurrency);
      
      const batchPromises = batch.map(async (menuItem) => {
        try {
          // Support both URL-based and function-based navigation
          if (!menuItem.url && (!menuItem.emit || menuItem.emit.length === 0)) {
            this.logger.warn(`Skipping menu item without URL or emit actions: ${menuItem.text}`);
            return null;
          }

          const menuPath = this.buildMenuPath(menuItem, menuItems);
          const analysis = await pageAnalyzer.analyzePage(menuItem, menuPath);
          
          pageAnalyses.set(menuItem.id, analysis);
          this.progressTracker.increment();
          
          return analysis;
        } catch (error) {
          this.logger.error(`Failed to analyze page for ${menuItem.text}:`, error);
          this.progressTracker.increment();
          return null;
        }
      });

      await Promise.all(batchPromises);

      // Add delay between batches
      if (i + concurrency < menuItems.length) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    this.progressTracker.finish();
    return pageAnalyses;
  }

  private async generateFunctionalities(
    menuItems: MenuItem[], 
    pageAnalyses: Map<string, PageAnalysis>
  ): Promise<MenuFunctionality[]> {
    
    const requests: LLMAnalysisRequest[] = [];
    
    for (const menuItem of menuItems) {
      const pageAnalysis = pageAnalyses.get(menuItem.id);
      if (pageAnalysis) {
        const menuPath = this.buildMenuPath(menuItem, menuItems);
        requests.push({
          menuItem,
          pageContent: pageAnalysis.content,
          context: menuPath.join(' > ')
        });
      }
    }

    this.progressTracker.start(requests.length, 'Generating descriptions');

    const functionalities = await this.llmAnalyzer.batchAnalyze(requests);

    // Update progress as each analysis completes
    functionalities.forEach(() => this.progressTracker.increment());
    this.progressTracker.finish();

    return functionalities;
  }

  private buildMenuPath(menuItem: MenuItem, allMenuItems: MenuItem[]): string[] {
    const path: string[] = [];
    let current: MenuItem | undefined = menuItem;

    while (current) {
      path.unshift(current.text);
      current = allMenuItems.find(item => item.id === current?.parentId);
    }

    return path;
  }

  async analyzeSingleMenu(menuUrl: string, menuName: string): Promise<MenuFunctionality> {
    try {
      await this.menuCrawler.initialize();
      await this.menuCrawler.login();

      const page = await this.menuCrawler.getPage();
      const pageAnalyzer = new PageAnalyzer(page, this.logger, this.config.onMenuOpen);

      // Create a mock menu item
      const menuItem: MenuItem = {
        id: 'single-analysis',
        text: menuName,
        url: menuUrl,
        level: 0,
        hasSubmenu: false
      };

      // Analyze the page
      const pageAnalysis = await pageAnalyzer.analyzePage(menuItem, [menuName]);

      // Generate functionality description
      const request: LLMAnalysisRequest = {
        menuItem,
        pageContent: pageAnalysis.content,
        context: menuName
      };

      const functionality = await this.llmAnalyzer.analyzeMenuFunctionality(request);
      
      return functionality;

    } finally {
      await this.menuCrawler.close();
    }
  }
}