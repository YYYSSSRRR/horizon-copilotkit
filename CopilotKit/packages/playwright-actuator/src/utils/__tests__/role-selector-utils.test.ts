/**
 * Role Selector Utils Unit Tests
 * 专门测试 XPath 生成逻辑
 */

import {
  buildRoleXPathWithName,
  getRoleSelector,
  elementMatchesAccessibleName,
  buildGetByLabelSelector,
  buildGetByTextSelector
} from '../role-selector-utils.js';

describe('role-selector-utils', () => {
  describe('buildRoleXPathWithName', () => {
    it('should generate valid XPath for role with name', () => {
      const xpath = buildRoleXPathWithName('row', '名称 告警ID 分组名称', { exact: true });
      
      // XPath 不应该包含无效的 //[ 格式
      expect(xpath).not.toContain('//[@role="row"]');
      // 应该包含有效的 //*[@role="row"] 格式
      expect(xpath).toContain('//*[@role="row"]');
      // 应该包含名称匹配条件
      expect(xpath).toContain('名称 告警ID 分组名称');
    });

    it('should handle role selectors with empty tag names correctly', () => {
      // 测试纯属性选择器 [role="row"] 的情况
      const xpath = buildRoleXPathWithName('row', 'test', { exact: true });
      
      // 验证生成的 XPath 是有效的
      expect(xpath).toMatch(/\/\/\*\[@role="row"\]/);
      expect(() => {
        document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      }).not.toThrow();
    });

    it('should generate valid XPath for multiple selectors', () => {
      // 测试包含多个选择器的角色
      const xpath = buildRoleXPathWithName('button', 'Submit', { exact: true });
      
      // 确保生成的 XPath 是有效的
      expect(xpath).toBeTruthy();
      expect(() => {
        document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      }).not.toThrow();
    });

    it('should handle exact vs non-exact matching', () => {
      const exactXPath = buildRoleXPathWithName('button', 'Click', { exact: true });
      const partialXPath = buildRoleXPathWithName('button', 'Click', { exact: false });
      
      // 精确匹配应该使用 = 
      expect(exactXPath).toContain('="Click"');
      // 部分匹配应该使用 contains
      expect(partialXPath).toContain('contains(');
    });

    it('should handle complex attribute selectors correctly', () => {
      // 测试复杂的选择器，如 input[type="button"]
      const xpath = buildRoleXPathWithName('textbox', 'Search', { exact: true });
      
      // 应该正确处理 input 标签的各种 type 属性
      expect(xpath).toBeTruthy();
      expect(() => {
        document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      }).not.toThrow();
    });
  });

  describe('getRoleSelector', () => {
    it('should return correct CSS selector for known roles', () => {
      expect(getRoleSelector('button')).toContain('button');
      expect(getRoleSelector('button')).toContain('[role="button"]');
      
      expect(getRoleSelector('row')).toContain('tr');
      expect(getRoleSelector('row')).toContain('[role="row"]');
    });

    it('should handle heading with level', () => {
      expect(getRoleSelector('heading', { level: 1 })).toContain('h1');
      expect(getRoleSelector('heading', { level: 2 })).toContain('h2');
    });

    it('should fallback to role attribute for unknown roles', () => {
      expect(getRoleSelector('unknown-role')).toBe('[role="unknown-role"]');
    });
  });

  describe('elementMatchesAccessibleName', () => {
    let element: HTMLElement;

    beforeEach(() => {
      element = document.createElement('button');
      document.body.appendChild(element);
    });

    afterEach(() => {
      element.remove();
    });

    it('should match aria-label', () => {
      element.setAttribute('aria-label', 'Test Button');
      expect(elementMatchesAccessibleName(element, 'Test Button', true)).toBe(true);
      expect(elementMatchesAccessibleName(element, 'Test', false)).toBe(true);
      expect(elementMatchesAccessibleName(element, 'Other', true)).toBe(false);
    });

    it('should match empty string for elements without accessible name', () => {
      expect(elementMatchesAccessibleName(element, '', true)).toBe(true);
      
      element.setAttribute('aria-label', 'Has label');
      expect(elementMatchesAccessibleName(element, '', true)).toBe(false);
    });

    it('should match text content', () => {
      element.textContent = 'Button Text';
      expect(elementMatchesAccessibleName(element, 'Button Text', true)).toBe(true);
      expect(elementMatchesAccessibleName(element, 'Button', false)).toBe(true);
    });

    it('should match title attribute', () => {
      element.setAttribute('title', 'Button Title');
      expect(elementMatchesAccessibleName(element, 'Button Title', true)).toBe(true);
    });

    it('should match table row accessible name from cell contents', () => {
      // 创建表格行结构，模拟用户提供的 HTML
      const table = document.createElement('table');
      const thead = document.createElement('thead');
      const row = document.createElement('tr');
      
      // 添加复选框单元格（应该被忽略或提取正确文本）
      const checkboxCell = document.createElement('th');
      checkboxCell.className = 'eui-table-cell eui-table-selection-cell';
      checkboxCell.innerHTML = `
        <label class="eui-checkbox-pro-wrapper">
          <span class="eui-checkbox-pro">
            <input class="eui-checkbox-pro-input" type="checkbox">
            <span class="eui-checkbox-pro-inner"></span>
          </span>
        </label>
      `;
      
      // 添加名称单元格
      const nameCell = document.createElement('th');
      nameCell.title = '名称';
      nameCell.className = 'eui-table-cell eui-table-cell-ellipsis';
      nameCell.innerHTML = `
        <div class="eui-table-column-sorter">
          <div class="eui-table-column-sorter-title eui-table-column-title-content">名称</div>
          <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
        </div>
        <div class="eui-table-resizable-bar"></div>
      `;
      
      // 添加告警ID单元格
      const idCell = document.createElement('th');
      idCell.title = '告警ID';
      idCell.className = 'eui-table-cell eui-table-cell-ellipsis';
      idCell.innerHTML = `
        <div class="eui-table-column-sorter">
          <div class="eui-table-column-sorter-title eui-table-column-title-content">告警ID</div>
          <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
        </div>
        <div class="eui-table-resizable-bar"></div>
      `;
      
      // 添加分组名称单元格
      const groupCell = document.createElement('th');
      groupCell.title = '分组名称';
      groupCell.className = 'eui-table-cell eui-table-cell-ellipsis';
      groupCell.innerHTML = `
        <div class="eui-table-column-sorter">
          <div class="eui-table-column-sorter-title eui-table-column-title-content">分组名称</div>
          <span class="eui-table-sorter eui-table-sorter-aui3" tabindex="0"></span>
        </div>
        <div class="eui-table-resizable-bar"></div>
      `;
      
      row.appendChild(checkboxCell);
      row.appendChild(nameCell);
      row.appendChild(idCell);
      row.appendChild(groupCell);
      thead.appendChild(row);
      table.appendChild(thead);
      document.body.appendChild(table);
      
      // 测试表格行能否匹配包含的文本
      expect(elementMatchesAccessibleName(row, '名称 告警ID 分组名称', true)).toBe(true);
      expect(elementMatchesAccessibleName(row, '名称 告警ID', false)).toBe(true);
      expect(elementMatchesAccessibleName(row, '不存在的文本', true)).toBe(false);
      
      // 清理
      table.remove();
    });

    it('should handle table rows with mixed content correctly', () => {
      const row = document.createElement('tr');
      
      // 单元格1：只有文本
      const cell1 = document.createElement('td');
      cell1.textContent = 'Cell 1';
      
      // 单元格2：有复杂结构
      const cell2 = document.createElement('td');
      cell2.innerHTML = '<div>Cell <span>2</span></div>';
      
      // 单元格3：有aria-label
      const cell3 = document.createElement('td');
      cell3.setAttribute('aria-label', 'Cell 3 Label');
      cell3.textContent = 'Cell 3 Text'; // 应该使用 aria-label
      
      row.appendChild(cell1);
      row.appendChild(cell2);
      row.appendChild(cell3);
      document.body.appendChild(row);
      
      // 应该匹配所有单元格文本的组合
      expect(elementMatchesAccessibleName(row, 'Cell 1 Cell 2 Cell 3 Label', true)).toBe(true);
      expect(elementMatchesAccessibleName(row, 'Cell 1', false)).toBe(true);
      expect(elementMatchesAccessibleName(row, 'Cell 3 Label', false)).toBe(true);
      
      // 清理
      row.remove();
    });
  });

  describe('buildGetByLabelSelector', () => {
    it('should generate XPath for label association', () => {
      const selector = buildGetByLabelSelector('Username', true);
      expect(selector.startsWith('xpath=')).toBe(true);
      expect(selector).toContain('Username');
    });

    it('should handle exact vs partial matching', () => {
      const exactSelector = buildGetByLabelSelector('Username', true);
      const partialSelector = buildGetByLabelSelector('Username', false);
      
      expect(exactSelector).toContain('="Username"');
      expect(partialSelector).toContain('contains(');
    });
  });

  describe('buildGetByTextSelector', () => {
    it('should generate XPath for text matching', () => {
      const selector = buildGetByTextSelector('Click me');
      expect(selector.startsWith('xpath=')).toBe(true);
      expect(selector).toContain('Click me');
    });

    it('should handle exact vs partial text matching', () => {
      const exactSelector = buildGetByTextSelector('Click', true);
      const partialSelector = buildGetByTextSelector('Click', false);
      
      expect(exactSelector).toContain('="Click"');
      expect(partialSelector).toContain('contains(');
    });
  });

  describe('XPath Validation Tests', () => {
    it('should generate valid XPath expressions that can be evaluated', () => {
      const testCases = [
        { role: 'row', name: '名称 告警ID 分组名称' },
        { role: 'button', name: 'Submit' },
        { role: 'textbox', name: 'Search' },
        { role: 'checkbox', name: '' },
        { role: 'link', name: 'Home Page' }
      ];

      testCases.forEach(({ role, name }) => {
        const xpath = buildRoleXPathWithName(role, name, { exact: true });
        expect(() => {
          document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        }).not.toThrow(`XPath should be valid for role=${role}, name=${name}: ${xpath}`);
      });
    });

    it('should not generate XPath with invalid syntax like //[@attr]', () => {
      const xpath = buildRoleXPathWithName('row', 'test', { exact: true });
      
      // 不应该包含无效的 //[ 语法
      expect(xpath).not.toMatch(/\/\/\[@/);
      // 应该包含有效的 //*[@ 语法
      expect(xpath).toMatch(/\/\/\*\[@/);
    });
  });
});