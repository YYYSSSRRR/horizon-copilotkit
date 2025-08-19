import { Browser, Page, chromium } from 'playwright';
import { MenuItem, MenuConfig, LoginConfig } from '../types';
import { Logger } from '../utils/Logger';

export class MenuCrawler {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private logger: Logger;
  private config: MenuConfig;

  constructor(config: MenuConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  async initialize(): Promise<void> {
    this.logger.info('Initializing browser...');
    this.browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    this.page = await this.browser.newPage({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      javaScriptEnabled: false  // 禁用JavaScript避免jQuery错误
    });

    // Set longer timeout
    this.page.setDefaultTimeout(this.config.waitTimeout || 30000);
    
    this.logger.info('Browser initialized successfully');
  }

  async login(): Promise<void> {
    if (!this.config.loginConfig || !this.page) {
      this.logger.info('No login configuration or page available, skipping login');
      return;
    }

    const loginConfig = this.config.loginConfig;
    
    try {
      // Navigate to login page
      await this.page.goto(loginConfig.loginUrl);
      await this.page.waitForLoadState('networkidle');
      this.logger.info('Login page loaded successfully');

      // Wait for login form elements
      try {
        await this.page.waitForSelector(loginConfig.usernameSelector, { timeout: 10000 });
        await this.page.waitForSelector(loginConfig.passwordSelector, { timeout: 10000 });
        await this.page.waitForSelector(loginConfig.submitSelector, { timeout: 10000 });
      } catch (selectorError) {
        const errorMsg = selectorError instanceof Error ? selectorError.message : String(selectorError);
        throw new Error(`Login form elements not found: ${errorMsg}. Check selectors: ${loginConfig.usernameSelector}, ${loginConfig.passwordSelector}, ${loginConfig.submitSelector}`);
      }

      // Fill login form
      await this.page.fill(loginConfig.usernameSelector, loginConfig.username);
      
      await this.page.fill(loginConfig.passwordSelector, loginConfig.password);
      
      await this.page.click(loginConfig.submitSelector);

      // Wait for login success
      if (loginConfig.successSelector) {
        try {
          await this.page.waitForSelector(loginConfig.successSelector, { timeout: 30000 });
          this.logger.info(`Login success confirmed by selector: ${loginConfig.successSelector}`);
        } catch (successError) {
          // Try to check for common error indicators
          const errorSelectors = ['.error', '.alert-danger', '[role="alert"]', '.login-error', '.error-message'];
          let errorMessage = '';
          
          for (const errorSelector of errorSelectors) {
            try {
              const errorElement = await this.page.$(errorSelector);
              if (errorElement) {
                const errorText = await errorElement.textContent();
                if (errorText?.trim()) {
                  errorMessage = errorText.trim();
                  break;
                }
              }
            } catch (e) {
              // Continue to next selector
            }
          }
          
          const message = errorMessage 
            ? `Login failed: ${errorMessage}` 
            : `Login may have failed - success selector '${loginConfig.successSelector}' not found within 30 seconds`;
          throw new Error(message);
        }
      } else {
        // Fallback: wait for page to stabilize
        await this.page.waitForLoadState('networkidle');
        this.logger.info('Login completed (no success selector specified)');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.logger.error(`Login failed: ${errorMsg}`);
      
      // Add helpful debugging information
      if (errorMsg.includes('timeout')) {
        this.logger.error('Login timeout - possible causes:');
        this.logger.error('  - Network connectivity issues');
        this.logger.error('  - Incorrect login URL or selectors');
        this.logger.error('  - Page loading too slowly');
      } else if (errorMsg.includes('not found')) {
        this.logger.error('Element not found - possible causes:');
        this.logger.error('  - Incorrect CSS selectors');
        this.logger.error('  - Page structure changed');
        this.logger.error('  - JavaScript not fully loaded');
      }
      
      throw new Error(`MenuCrawler login failed: ${errorMsg}`);
    }
  }

  async discoverMenus(): Promise<MenuItem[]> {
    if (!this.page) {
      throw new Error('Browser not initialized');
    }

    this.logger.info('Discovering menu structure...');
    
    // Navigate to base URL if provided
    if (this.config.baseUrl) {
      await this.page.goto(this.config.baseUrl);
      await this.page.waitForLoadState('networkidle');
    }

    const allMenuItems: MenuItem[] = [];
    
    // Try multiple menu selectors
    for (const selector of this.config.menuSelectors || []) {
      try {
        const menuItems = await this.extractMenuItems(selector);
        allMenuItems.push(...menuItems);
        this.logger.info(`Found ${menuItems.length} menu items with selector: ${selector}`);
      } catch (error) {
        this.logger.warn(`Failed to extract menu items with selector ${selector}:`, error);
      }
    }

    // Remove duplicates and filter excluded patterns
    const uniqueMenus = this.deduplicateMenus(allMenuItems);
    const filteredMenus = this.filterMenus(uniqueMenus);
    
    this.logger.info(`Total discovered menus: ${filteredMenus.length}`);
    return filteredMenus;
  }

  private async extractMenuItems(selector: string, level: number = 0, parentId?: string): Promise<MenuItem[]> {
    if (!this.page || level > (this.config.maxDepth || 3)) {
      return [];
    }

    const menuItems: MenuItem[] = [];
    
    // Get all menu items at current level
    const elements = await this.page.locator(selector).all();
    
    for (let i = 0; i < elements.length; i++) {
      const element = elements[i];
      
      try {
        // Extract menu item information
        const text = await element.textContent();
        const href = await element.getAttribute('href');
        const hasSubmenu = await element.locator('[aria-haspopup="true"], .submenu, .dropdown').count() > 0;
        
        if (!text?.trim()) continue;

        // Generate unique ID
        const id = `${parentId || 'root'}-${level}-${i}`;
        
        // Construct full URL
        let url = '';
        if (href) {
          url = href.startsWith('http') ? href : new URL(href, this.config.baseUrl || '').toString();
        }

        const menuItem: MenuItem = {
          id,
          text: text.trim(),
          url: url || undefined,
          level,
          parentId,
          hasSubmenu,
          elementSelector: await this.generateSelector(element)
        };

        menuItems.push(menuItem);

        // Extract submenu items if exists
        if (hasSubmenu && level < (this.config.maxDepth || 3)) {
          try {
            // Try to expand submenu
            await element.hover();
            await this.page.waitForTimeout(500);
            
            // Look for submenu items
            const submenuSelector = `${selector} .submenu a, ${selector} .dropdown a`;
            const submenuItems = await this.extractMenuItems(submenuSelector, level + 1, id);
            menuItems.push(...submenuItems);
            
          } catch (error) {
            this.logger.warn(`Failed to extract submenu for ${text}:`, error);
          }
        }
        
      } catch (error) {
        this.logger.warn(`Failed to process menu element ${i}:`, error);
      }
    }

    return menuItems;
  }

  private async generateSelector(element: any): Promise<string> {
    try {
      // Try to generate a unique selector for the element
      const id = await element.getAttribute('id');
      if (id) return `#${id}`;

      const className = await element.getAttribute('class');
      if (className) {
        const classes = className.split(' ').filter((c: string) => c.trim()).slice(0, 2);
        return `.${classes.join('.')}`;
      }

      // Fallback to tag name
      const tagName = await element.evaluate((el: Element) => el.tagName.toLowerCase());
      return tagName;
      
    } catch (error) {
      return '*';
    }
  }

  private deduplicateMenus(menuItems: MenuItem[]): MenuItem[] {
    const seen = new Set<string>();
    return menuItems.filter(item => {
      const key = `${item.text}-${item.url}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  private filterMenus(menuItems: MenuItem[]): MenuItem[] {
    return menuItems.filter(item => {
      // Filter out excluded patterns
      for (const pattern of this.config.excludePatterns || []) {
        if ((item.url && item.url.includes(pattern)) || 
            item.text.toLowerCase().includes(pattern.toLowerCase())) {
          return false;
        }
      }
      
      // Allow items with URL or emit actions or submenus
      if (!item.url && !item.emit?.length && !item.hasSubmenu) {
        return false;
      }
      
      return true;
    });
  }

  async getPage(): Promise<Page> {
    if (!this.page) {
      throw new Error('Browser not initialized');
    }
    return this.page;
  }

  async close(): Promise<void> {
    if (this.page) {
      await this.page.close();
    }
    if (this.browser) {
      await this.browser.close();
    }
    this.logger.info('Browser closed');
  }
}