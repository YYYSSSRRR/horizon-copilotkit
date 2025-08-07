/**
 * LocatorAdapter Table Integration Tests
 * 专门测试表格行匹配功能的集成测试
 */

// 不使用 mock，直接导入真实的实现
import LocatorAdapter from '../locator-adapter.js';

// Setup jsdom environment
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
  url: 'http://localhost',
  pretendToBeVisual: true,
  resources: 'usable'
});

// Setup global environment
global.document = dom.window.document;
global.window = dom.window as any;
global.Node = dom.window.Node;
global.Element = dom.window.Element;
global.HTMLElement = dom.window.HTMLElement;
global.HTMLInputElement = dom.window.HTMLInputElement;
global.HTMLTextAreaElement = dom.window.HTMLTextAreaElement;
global.HTMLSelectElement = dom.window.HTMLSelectElement;
global.HTMLButtonElement = dom.window.HTMLButtonElement;
global.XPathResult = dom.window.XPathResult;

// Mock page object with minimal required functionality
const createMockPage = () => ({
  waitManager: {
    waitForCondition: jest.fn()
  },
  eventSimulator: {
    simulateClick: jest.fn(),
    simulateDoubleClick: jest.fn(),
    simulateKeyPress: jest.fn(),
    simulateTyping: jest.fn(),
    simulateHover: jest.fn()
  },
  scrollIntoViewIfNeeded: jest.fn()
});

describe('LocatorAdapter Table Integration Tests', () => {
  let mockPage: any;

  beforeEach(() => {
    // Clear DOM
    document.body.innerHTML = '';
    
    // Create fresh mock page
    mockPage = createMockPage();
    
    // Mock global PlaywrightLogger if it exists
    (global as any).window.PlaywrightLogger = function() {
      return {
        info: jest.fn(),
        debug: jest.fn(),
        warn: jest.fn(),
        error: jest.fn()
      };
    };
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('getByRole with table rows', () => {
    it('should find table row by accessible name from header cells', async () => {
      // 创建与用户问题中相同的表格结构
      const tableHTML = `
        <table>
          <thead>
            <tr>
              <th tabindex="0" class="eui-table-cell eui-table-selection-cell">
                <label class="eui-checkbox-pro-wrapper">
                  <span class="eui-checkbox-pro">
                    <input class="eui-checkbox-pro-input" type="checkbox">
                    <span class="eui-checkbox-pro-inner"></span>
                  </span>
                </label>
              </th>
              <th title="名称" tabindex="0" class="eui-table-cell eui-table-cell-ellipsis">
                <div class="eui-table-column-sorter">
                  <div class="eui-table-column-sorter-title eui-table-column-title-content">名称</div>
                  <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
                </div>
                <div class="eui-table-resizable-bar"></div>
              </th>
              <th title="告警ID" tabindex="0" class="eui-table-cell eui-table-cell-ellipsis">
                <div class="eui-table-column-sorter">
                  <div class="eui-table-column-sorter-title eui-table-column-title-content">告警ID</div>
                  <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
                </div>
                <div class="eui-table-resizable-bar"></div>
              </th>
              <th title="分组名称" tabindex="0" class="eui-table-cell eui-table-cell-ellipsis">
                <div class="eui-table-column-sorter">
                  <div class="eui-table-column-sorter-title eui-table-column-title-content">分组名称</div>
                  <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
                </div>
                <div class="eui-table-resizable-bar" style="transform: translateX(0%);"></div>
              </th>
            </tr>
          </thead>
        </table>
      `;
      
      document.body.innerHTML = tableHTML;
      const row = document.querySelector('tr')!;
      
      // 创建页面级别的 LocatorAdapter
      const pageLocator = new LocatorAdapter('*', mockPage);
      
      // 使用 getByRole 查找行
      const rowLocator = pageLocator.getByRole('row', { 
        name: '名称 告警ID 分组名称', 
        exact: true 
      });
      
      // 验证能够找到该行
      const foundElement = await rowLocator.getElement();
      expect(foundElement).toBe(row);
    });

    it('should find table row by partial accessible name match', async () => {
      const tableHTML = `
        <table>
          <tbody>
            <tr>
              <td>产品名称</td>
              <td>PRD-001</td>
              <td>电子产品</td>
            </tr>
            <tr>
              <td>服务名称</td>
              <td>SRV-001</td>
              <td>技术服务</td>
            </tr>
          </tbody>
        </table>
      `;
      
      document.body.innerHTML = tableHTML;
      const rows = document.querySelectorAll('tr');
      
      const pageLocator = new LocatorAdapter('*', mockPage);
      
      // 使用部分匹配查找第一行
      const row1Locator = pageLocator.getByRole('row', { 
        name: '产品名称', 
        exact: false 
      });
      
      const foundRow1 = await row1Locator.getElement();
      expect(foundRow1).toBe(rows[0]);
      
      // 使用部分匹配查找第二行
      const row2Locator = pageLocator.getByRole('row', { 
        name: '技术服务', 
        exact: false 
      });
      
      const foundRow2 = await row2Locator.getElement();
      expect(foundRow2).toBe(rows[1]);
    });

    it('should find specific table row when multiple rows exist', async () => {
      const tableHTML = `
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>告警ID</th>
              <th>分组名称</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>数据A</td>
              <td>ALM-001</td>
              <td>组A</td>
            </tr>
            <tr>
              <td>数据B</td>
              <td>ALM-002</td>
              <td>组B</td>
            </tr>
          </tbody>
        </table>
      `;
      
      document.body.innerHTML = tableHTML;
      const headerRow = document.querySelector('thead tr')!;
      const dataRows = document.querySelectorAll('tbody tr');
      
      const pageLocator = new LocatorAdapter('*', mockPage);
      
      // 查找表头行
      const headerLocator = pageLocator.getByRole('row', { 
        name: '名称 告警ID 分组名称', 
        exact: true 
      });
      
      const foundHeader = await headerLocator.getElement();
      expect(foundHeader).toBe(headerRow);
      
      // 查找特定数据行
      const dataRow1Locator = pageLocator.getByRole('row', { 
        name: '数据A ALM-001 组A', 
        exact: true 
      });
      
      const foundDataRow1 = await dataRow1Locator.getElement();
      expect(foundDataRow1).toBe(dataRows[0]);
      
      const dataRow2Locator = pageLocator.getByRole('row', { 
        name: '数据B ALM-002 组B', 
        exact: true 
      });
      
      const foundDataRow2 = await dataRow2Locator.getElement();
      expect(foundDataRow2).toBe(dataRows[1]);
    });

    it('should handle rows with complex nested structures', async () => {
      const tableHTML = `
        <table>
          <tr>
            <td>
              <div class="complex-cell">
                <span>嵌套</span>
                <div>
                  <p>文本</p>
                </div>
              </div>
            </td>
            <td aria-label="使用标签">
              忽略这个文本
            </td>
            <td>
              <button>按钮文本</button>
            </td>
          </tr>
        </table>
      `;
      
      document.body.innerHTML = tableHTML;
      const row = document.querySelector('tr')!;
      
      const pageLocator = new LocatorAdapter('*', mockPage);
      
      // 应该能通过部分匹配找到包含复杂结构的行
      const rowLocator = pageLocator.getByRole('row', { 
        name: '嵌套', 
        exact: false 
      });
      
      const foundElement = await rowLocator.getElement();
      expect(foundElement).toBe(row);
    });

    it('should not find row when accessible name does not match', async () => {
      const tableHTML = `
        <table>
          <tr>
            <td>实际文本</td>
            <td>另一个文本</td>
          </tr>
        </table>
      `;
      
      document.body.innerHTML = tableHTML;
      
      const pageLocator = new LocatorAdapter('*', mockPage);
      
      // 尝试匹配不存在的文本
      const rowLocator = pageLocator.getByRole('row', { 
        name: '不存在的文本', 
        exact: true 
      });
      
      await expect(rowLocator.getElement()).rejects.toThrow('找不到元素');
    });
  });

  describe('nested table row searching', () => {
    it('should find table row within a specific container', async () => {
      const html = `
        <div class="container1">
          <table>
            <tr><td>容器1 行1</td></tr>
          </table>
        </div>
        <div class="container2">
          <table>
            <tr><td>容器2 行1</td></tr>
          </table>
        </div>
      `;
      
      document.body.innerHTML = html;
      
      // 在特定容器中查找行
      const container2Locator = new LocatorAdapter('.container2', mockPage);
      const rowLocator = container2Locator.getByRole('row', { 
        name: '容器2 行1', 
        exact: true 
      });
      
      const foundElement = await rowLocator.getElement();
      expect(foundElement.textContent).toContain('容器2 行1');
    });
  });
});