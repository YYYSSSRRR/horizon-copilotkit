/// <reference path="../types/global.d.ts" />
import type { Logger } from '../../types/index.js';

/**
 * 等待管理器 - 处理各种等待机制
 */
class WaitManager {
  private readonly defaultTimeout: number;
  private readonly logger: Logger;

  constructor() {
    this.defaultTimeout = 30000;
    this.logger = (typeof window !== 'undefined' && window.PlaywrightLogger) 
      ? new window.PlaywrightLogger() 
      : console as unknown as Logger;
  }

  /**
   * 查询单个元素（支持 CSS、XPath 和 text）
   */
  querySelector(selector: string): Element | null {
    if (selector.startsWith('xpath=')) {
      const xpath = selector.substring(6);
      const result = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      return result.singleNodeValue as Element | null;
    } else if (selector.startsWith('text=')) {
      const text = selector.substring(5);
      // 使用 XPath 查找包含指定文本的元素
      const xpath = `//*[contains(normalize-space(text()), "${text}")]`;
      const result = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      return result.singleNodeValue as Element | null;
    } else {
      return document.querySelector(selector);
    }
  }

  /**
   * 等待元素出现
   */
  async waitForElement(selector: string, timeout: number = this.defaultTimeout): Promise<Element> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      // 立即检查
      const existing = this.querySelector(selector);
      if (existing) {
        this.logger.debug(`元素立即找到: ${selector}`);
        return resolve(existing);
      }

      let timeoutId: NodeJS.Timeout | undefined;
      let observer: MutationObserver | undefined;

      const cleanup = (): void => {
        if (timeoutId) clearTimeout(timeoutId);
        if (observer) observer.disconnect();
      };

      // 设置超时
      timeoutId = setTimeout(() => {
        cleanup();
        reject(new Error(`等待元素超时: ${selector} (${timeout}ms)`));
      }, timeout);

      // 监听 DOM 变化
      observer = new MutationObserver(() => {
        const element = this.querySelector(selector);
        if (element) {
          cleanup();
          const elapsed = Date.now() - startTime;
          this.logger.debug(`元素找到: ${selector} (${elapsed}ms)`);
          resolve(element);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true
      });
    });
  }

  /**
   * 等待条件满足
   */
  async waitForCondition<T>(
    conditionFn: () => T | Promise<T>, 
    timeout: number = this.defaultTimeout, 
    errorMessage: string = '等待条件超时'
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const check = async (): Promise<void> => {
        try {
          const result = await conditionFn();
          if (result) {
            const elapsed = Date.now() - startTime;
            this.logger.debug(`条件满足 (${elapsed}ms)`);
            resolve(result);
            return;
          }
        } catch (error) {
          // 继续等待，忽略错误
          this.logger.debug('条件检查出错，继续等待:', (error as Error).message);
        }

        if (Date.now() - startTime >= timeout) {
          reject(new Error(`${errorMessage} (${timeout}ms)`));
          return;
        }

        setTimeout(check, 100);
      };

      check();
    });
  }

  /**
   * 等待函数返回真值
   */
  async waitForFunction<T>(fn: () => T | Promise<T>, timeout: number = this.defaultTimeout): Promise<T> {
    return this.waitForCondition(fn, timeout, '等待函数条件超时');
  }

  /**
   * 等待 URL 变化
   */
  async waitForURL(urlPattern: string | RegExp, timeout: number = this.defaultTimeout): Promise<boolean> {
    return this.waitForCondition(
      () => {
        const currentUrl = window.location.href;
        if (typeof urlPattern === 'string') {
          return currentUrl.includes(urlPattern);
        }
        if (urlPattern instanceof RegExp) {
          return urlPattern.test(currentUrl);
        }
        return false;
      },
      timeout,
      `等待URL变化超时: ${urlPattern}`
    );
  }

  /**
   * 等待页面加载状态
   */
  async waitForLoadState(state: 'load' | 'domcontentloaded' | 'networkidle' = 'load'): Promise<void> {
    return new Promise((resolve) => {
      const checkState = (): void => {
        if (state === 'load' && document.readyState === 'complete') {
          this.logger.debug('页面完全加载');
          resolve();
        } else if (state === 'domcontentloaded' && document.readyState !== 'loading') {
          this.logger.debug('DOM 内容加载完成');
          resolve();
        } else if (state === 'networkidle') {
          // 简单实现：等待 500ms 无网络请求
          setTimeout(() => {
            this.logger.debug('网络空闲');
            resolve();
          }, 500);
        }
      };

      if (document.readyState === 'complete' && state === 'load') {
        resolve();
      } else if (document.readyState !== 'loading' && state === 'domcontentloaded') {
        resolve();
      } else {
        document.addEventListener('readystatechange', checkState, { once: true });
      }
    });
  }

  /**
   * 简单延时
   */
  async waitForTimeout(ms: number): Promise<void> {
    this.logger.debug(`等待 ${ms}ms`);
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}


// 导出给浏览器使用
if (typeof window !== 'undefined') {
  window.PlaywrightWaitManager = WaitManager;
}


// ES6 模块导出
export default WaitManager;