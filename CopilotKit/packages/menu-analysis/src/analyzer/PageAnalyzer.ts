import { Page } from 'playwright';
import * as cheerio from 'cheerio';
import { PageAnalysis, PageContent, FormInfo, TableInfo, ButtonInfo, LinkInfo, ImageInfo, PageMetadata, MenuItem } from '../types';
import { Logger } from '../utils/Logger';

export class PageAnalyzer {
  private page: Page;
  private logger: Logger;

  constructor(page: Page, logger: Logger, private onMenuOpen?: (page: Page, emit: string[]) => Promise<void>) {
    this.page = page;
    this.logger = logger;
  }

  async analyzePage(menuItem: MenuItem, menuPath: string[]): Promise<PageAnalysis> {
    this.logger.info(`Analyzing page: ${menuItem.text} ${menuItem.url ? `(${menuItem.url})` : '(function-based)'}`);

    try {
      // Navigate to the page using URL or function call
      if (menuItem.emit && this.onMenuOpen) {
        // Function-based navigation
        this.logger.info(`Opening page via function with emit: ${menuItem.emit.join(', ')}`);
        await this.onMenuOpen(this.page, menuItem.emit);
        
        // Wait for the page to load after function call
        await this.page.waitForTimeout(3000);
      } else if (menuItem.url) {
        // Traditional URL-based navigation
        await this.page.goto(menuItem.url, { waitUntil: 'networkidle' });
        await this.page.waitForTimeout(2000);
      } else {
        throw new Error(`MenuItem ${menuItem.text} has neither URL nor emit actions`);
      }

      // Extract page content
      const title = await this.page.title();
      const html = await this.page.content();
      const currentUrl = this.page.url();
      const content = await this.extractPageContent(html, currentUrl);

      return {
        url: currentUrl,
        title,
        menuPath,
        content,
        timestamp: new Date()
      };

    } catch (error) {
      this.logger.error(`Failed to analyze page ${menuItem.text}:`, error);
      throw error;
    }
  }

  private async extractPageContent(html: string, url: string): Promise<PageContent> {
    const $ = cheerio.load(html);
    
    // Remove script and style tags for cleaner text extraction
    $('script, style, nav, footer, .sidebar, .menu').remove();

    const content: PageContent = {
      html,
      text: this.extractCleanText($),
      forms: this.extractForms($),
      tables: this.extractTables($),
      buttons: this.extractButtons($),
      links: this.extractLinks($, url),
      images: this.extractImages($, url),
      metadata: this.extractMetadata($)
    };

    return content;
  }

  private extractCleanText($: cheerio.CheerioAPI): string {
    // Extract main content areas
    const contentSelectors = [
      'main', '.main', '#main',
      '.content', '#content', 
      '.page-content', '.main-content',
      'article', '.article',
      '.container', '.wrapper'
    ];

    let mainText = '';
    
    for (const selector of contentSelectors) {
      const element = $(selector).first();
      if (element.length > 0) {
        mainText = element.text().trim();
        if (mainText.length > 100) break; // Found substantial content
      }
    }

    // Fallback to body text if no main content found
    if (!mainText || mainText.length < 100) {
      mainText = $('body').text().trim();
    }

    // Clean up the text
    return mainText
      .replace(/\s+/g, ' ')
      .replace(/\n\s*\n/g, '\n')
      .trim()
      .substring(0, 5000); // Limit text length
  }

  private extractForms($: cheerio.CheerioAPI): FormInfo[] {
    const forms: FormInfo[] = [];

    $('form').each((_, formElement) => {
      const $form = $(formElement);
      const fields = this.extractFormFields($form);
      
      if (fields.length > 0) {
        forms.push({
          id: $form.attr('id'),
          action: $form.attr('action'),
          method: $form.attr('method') || 'GET',
          fields,
          purpose: this.inferFormPurpose($form, fields)
        });
      }
    });

    return forms;
  }

  private extractFormFields($form: cheerio.Cheerio<cheerio.Element>) {
    const fields: any[] = [];

    $form.find('input, select, textarea').each((_, fieldElement) => {
      const $field = $(fieldElement);
      const type = $field.attr('type') || $field.prop('tagName')?.toLowerCase() || 'text';
      
      // Skip hidden and submit buttons for analysis
      if (type === 'hidden' || type === 'submit') return;

      const field = {
        name: $field.attr('name'),
        type,
        label: this.findFieldLabel($field),
        placeholder: $field.attr('placeholder'),
        required: $field.attr('required') !== undefined,
        options: this.extractSelectOptions($field)
      };

      fields.push(field);
    });

    return fields;
  }

  private findFieldLabel($field: cheerio.Cheerio<cheerio.Element>): string | undefined {
    // Try to find associated label
    const fieldId = $field.attr('id');
    if (fieldId) {
      const label = $(`label[for="${fieldId}"]`).text().trim();
      if (label) return label;
    }

    // Try parent label
    const parentLabel = $field.closest('label').text().trim();
    if (parentLabel) return parentLabel;

    // Try previous sibling
    const prevLabel = $field.prev('label').text().trim();
    if (prevLabel) return prevLabel;

    // Try placeholder as fallback
    return $field.attr('placeholder');
  }

  private extractSelectOptions($field: cheerio.Cheerio<cheerio.Element>): string[] | undefined {
    if ($field.prop('tagName')?.toLowerCase() === 'select') {
      const options: string[] = [];
      $field.find('option').each((_, option) => {
        const text = $(option).text().trim();
        if (text && text !== 'Select...') {
          options.push(text);
        }
      });
      return options.length > 0 ? options : undefined;
    }
    return undefined;
  }

  private inferFormPurpose($form: cheerio.Cheerio<cheerio.Element>, fields: any[]): string {
    const formText = $form.text().toLowerCase();
    const fieldNames = fields.map(f => f.name?.toLowerCase() || '').join(' ');
    const combined = `${formText} ${fieldNames}`;

    if (combined.includes('search') || combined.includes('query')) return 'search';
    if (combined.includes('login') || combined.includes('signin')) return 'login';
    if (combined.includes('register') || combined.includes('signup')) return 'registration';
    if (combined.includes('contact') || combined.includes('message')) return 'contact';
    if (combined.includes('filter') || combined.includes('sort')) return 'filter';
    if (combined.includes('edit') || combined.includes('update')) return 'edit';
    if (combined.includes('create') || combined.includes('add') || combined.includes('new')) return 'create';
    if (combined.includes('delete') || combined.includes('remove')) return 'delete';
    if (combined.includes('upload') || combined.includes('file')) return 'upload';
    if (combined.includes('payment') || combined.includes('billing')) return 'payment';
    
    return 'data-entry';
  }

  private extractTables($: cheerio.CheerioAPI): TableInfo[] {
    const tables: TableInfo[] = [];

    $('table, [role="grid"], .table, .data-table').each((_, tableElement) => {
      const $table = $(tableElement);
      const headers = this.extractTableHeaders($table);
      const rowCount = this.countTableRows($table);
      
      if (headers.length > 0 || rowCount > 0) {
        tables.push({
          id: $table.attr('id'),
          headers,
          rowCount,
          hasActions: this.hasTableActions($table),
          purpose: this.inferTablePurpose($table, headers)
        });
      }
    });

    return tables;
  }

  private extractTableHeaders($table: cheerio.Cheerio<cheerio.Element>): string[] {
    const headers: string[] = [];
    
    $table.find('th, thead td, .table-header').each((_, headerElement) => {
      const text = $(headerElement).text().trim();
      if (text) headers.push(text);
    });

    return headers;
  }

  private countTableRows($table: cheerio.Cheerio<cheerio.Element>): number {
    return $table.find('tbody tr, .table-row').length;
  }

  private hasTableActions($table: cheerio.Cheerio<cheerio.Element>): boolean {
    return $table.find('button, .btn, .action, [role="button"]').length > 0;
  }

  private inferTablePurpose($table: cheerio.Cheerio<cheerio.Element>, headers: string[]): string {
    const tableText = $table.text().toLowerCase();
    const headerText = headers.join(' ').toLowerCase();
    const combined = `${tableText} ${headerText}`;

    if (combined.includes('user') || combined.includes('employee')) return 'user-management';
    if (combined.includes('order') || combined.includes('transaction')) return 'order-management';
    if (combined.includes('product') || combined.includes('item')) return 'product-catalog';
    if (combined.includes('report') || combined.includes('statistic')) return 'reporting';
    if (combined.includes('log') || combined.includes('history')) return 'audit-trail';
    if (combined.includes('permission') || combined.includes('role')) return 'access-control';
    if (combined.includes('config') || combined.includes('setting')) return 'configuration';
    if (combined.includes('data') || combined.includes('record')) return 'data-management';
    
    return 'data-display';
  }

  private extractButtons($: cheerio.CheerioAPI): ButtonInfo[] {
    const buttons: ButtonInfo[] = [];

    $('button, input[type="submit"], input[type="button"], .btn, [role="button"]').each((_, buttonElement) => {
      const $button = $(buttonElement);
      const text = $button.text().trim() || $button.attr('value') || $button.attr('title') || '';
      
      if (text) {
        buttons.push({
          text,
          type: $button.attr('type'),
          purpose: this.inferButtonPurpose(text),
          action: $button.attr('onclick') || $button.attr('data-action')
        });
      }
    });

    return buttons;
  }

  private inferButtonPurpose(text: string): string {
    const lowerText = text.toLowerCase();
    
    if (lowerText.includes('save') || lowerText.includes('submit')) return 'save';
    if (lowerText.includes('edit') || lowerText.includes('modify')) return 'edit';
    if (lowerText.includes('delete') || lowerText.includes('remove')) return 'delete';
    if (lowerText.includes('create') || lowerText.includes('add') || lowerText.includes('new')) return 'create';
    if (lowerText.includes('search') || lowerText.includes('find')) return 'search';
    if (lowerText.includes('export') || lowerText.includes('download')) return 'export';
    if (lowerText.includes('import') || lowerText.includes('upload')) return 'import';
    if (lowerText.includes('copy') || lowerText.includes('duplicate')) return 'copy';
    if (lowerText.includes('print')) return 'print';
    if (lowerText.includes('cancel') || lowerText.includes('close')) return 'cancel';
    if (lowerText.includes('confirm') || lowerText.includes('ok')) return 'confirm';
    if (lowerText.includes('reset') || lowerText.includes('clear')) return 'reset';
    
    return 'action';
  }

  private extractLinks($: cheerio.CheerioAPI, baseUrl: string): LinkInfo[] {
    const links: LinkInfo[] = [];
    const base = new URL(baseUrl);

    $('a[href]').each((_, linkElement) => {
      const $link = $(linkElement);
      const href = $link.attr('href');
      const text = $link.text().trim();
      
      if (href && text) {
        try {
          const url = new URL(href, baseUrl);
          links.push({
            text,
            href: url.toString(),
            isInternal: url.hostname === base.hostname
          });
        } catch (error) {
          // Invalid URL, skip
        }
      }
    });

    return links;
  }

  private extractImages($: cheerio.CheerioAPI, baseUrl: string): ImageInfo[] {
    const images: ImageInfo[] = [];

    $('img[src]').each((_, imgElement) => {
      const $img = $(imgElement);
      const src = $img.attr('src');
      const alt = $img.attr('alt');
      
      if (src) {
        try {
          const url = new URL(src, baseUrl);
          images.push({
            src: url.toString(),
            alt,
            purpose: this.inferImagePurpose($img, alt)
          });
        } catch (error) {
          // Invalid URL, skip
        }
      }
    });

    return images;
  }

  private inferImagePurpose($img: cheerio.Cheerio<cheerio.Element>, alt?: string): string {
    const className = $img.attr('class') || '';
    const altText = (alt || '').toLowerCase();
    
    if (className.includes('logo') || altText.includes('logo')) return 'logo';
    if (className.includes('icon') || altText.includes('icon')) return 'icon';
    if (className.includes('avatar') || altText.includes('avatar')) return 'avatar';
    if (className.includes('banner') || altText.includes('banner')) return 'banner';
    if (className.includes('chart') || altText.includes('chart')) return 'chart';
    
    return 'content';
  }

  private extractMetadata($: cheerio.CheerioAPI): PageMetadata {
    const breadcrumbs: string[] = [];
    
    // Extract breadcrumbs
    $('.breadcrumb, .breadcrumbs, [aria-label="breadcrumb"]').find('a, span').each((_, element) => {
      const text = $(element).text().trim();
      if (text) breadcrumbs.push(text);
    });

    return {
      description: $('meta[name="description"]').attr('content'),
      keywords: $('meta[name="keywords"]').attr('content')?.split(',').map(k => k.trim()),
      breadcrumbs,
      pageType: this.inferPageType($)
    };
  }

  private inferPageType($: cheerio.CheerioAPI): string {
    const title = $('title').text().toLowerCase();
    const bodyClass = $('body').attr('class') || '';
    const combined = `${title} ${bodyClass}`.toLowerCase();

    if (combined.includes('dashboard')) return 'dashboard';
    if (combined.includes('list') || combined.includes('index')) return 'list';
    if (combined.includes('detail') || combined.includes('view')) return 'detail';
    if (combined.includes('edit') || combined.includes('form')) return 'form';
    if (combined.includes('report')) return 'report';
    if (combined.includes('setting') || combined.includes('config')) return 'settings';
    if (combined.includes('admin')) return 'admin';
    
    return 'content';
  }
}