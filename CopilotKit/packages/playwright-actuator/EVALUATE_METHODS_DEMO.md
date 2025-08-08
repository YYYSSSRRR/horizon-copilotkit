# Evaluate Methods Demo

这个文档演示了新添加的 `evaluate`、`evaluateAll` 和 `evaluateHandle` 方法的使用。

## evaluate(pageFunction, arg?)

在第一个匹配的元素上执行JavaScript函数，返回序列化的结果。

```javascript
// 基本用法 - 获取元素信息
const locator = page.locator('.my-element');
const elementInfo = await locator.evaluate(el => ({
  tagName: el.tagName,
  textContent: el.textContent,
  id: el.id,
  className: el.className
}));

// 传递参数
const modifiedText = await locator.evaluate((el, suffix) => {
  return el.textContent + suffix;
}, ' - Modified');

// 获取计算样式
const styles = await locator.evaluate(el => {
  const computedStyle = window.getComputedStyle(el);
  return {
    color: computedStyle.color,
    fontSize: computedStyle.fontSize,
    display: computedStyle.display
  };
});

// 获取元素位置和尺寸
const boundingBox = await locator.evaluate(el => {
  const rect = el.getBoundingClientRect();
  return {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height
  };
});
```

## evaluateAll(pageFunction, arg?)

在所有匹配的元素上执行JavaScript函数。

```javascript
// 获取所有匹配元素的文本
const allTexts = await page.locator('.item').evaluateAll(elements => {
  return elements.map(el => el.textContent);
});

// 统计元素信息
const stats = await page.locator('input').evaluateAll(elements => {
  return {
    total: elements.length,
    byType: elements.reduce((acc, el) => {
      const type = el.type || 'text';
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {}),
    enabled: elements.filter(el => !el.disabled).length
  };
});

// 批量操作元素
await page.locator('.highlight').evaluateAll((elements, className) => {
  elements.forEach(el => {
    el.classList.add(className);
  });
}, 'active');
```

## evaluateHandle(pageFunction, arg?)

类似于 `evaluate`，但可以返回不可序列化的值（如DOM元素引用）。

```javascript
// 返回DOM元素引用
const parentElement = await locator.evaluateHandle(el => el.parentElement);

// 获取子元素集合
const childNodes = await locator.evaluateHandle(el => el.childNodes);

// 获取表单引用
const formElement = await page.locator('input').evaluateHandle(el => el.form);

// 执行复杂的DOM操作并返回结果
const manipulationResult = await locator.evaluateHandle((el, config) => {
  // 执行一些DOM操作
  const newElement = document.createElement('div');
  newElement.textContent = config.text;
  el.appendChild(newElement);
  
  // 返回新创建的元素（不可序列化）
  return newElement;
}, { text: 'New content' });
```

## 实际使用场景

### 场景1：表格数据提取

```javascript
// 提取表格所有行的数据
const tableData = await page.locator('table tbody tr').evaluateAll(rows => {
  return rows.map(row => {
    const cells = row.querySelectorAll('td');
    return Array.from(cells).map(cell => cell.textContent.trim());
  });
});
```

### 场景2：表单验证状态检查

```javascript
// 检查表单验证状态
const validationInfo = await page.locator('form').evaluate(form => {
  const inputs = form.querySelectorAll('input, select, textarea');
  return {
    isValid: form.checkValidity(),
    invalidFields: Array.from(inputs)
      .filter(input => !input.checkValidity())
      .map(input => ({
        name: input.name,
        validationMessage: input.validationMessage
      }))
  };
});
```

### 场景3：动态内容监控

```javascript
// 获取动态内容的变化
const contentSnapshot = await page.locator('.dynamic-content').evaluate(el => {
  return {
    timestamp: Date.now(),
    content: el.innerHTML,
    childCount: el.children.length,
    hasScrollbar: el.scrollHeight > el.clientHeight
  };
});
```

## 错误处理

所有evaluate方法都包含错误处理：

```javascript
try {
  const result = await locator.evaluate(el => {
    if (!el.someProperty) {
      throw new Error('Element is missing required property');
    }
    return el.someProperty.value;
  });
} catch (error) {
  console.error('Evaluation failed:', error.message);
}
```

## 注意事项

1. **序列化限制**：`evaluate` 方法只能返回JSON可序列化的值
2. **上下文隔离**：函数在DOM上下文中执行，无法访问Node.js作用域的变量
3. **异步支持**：所有方法都支持async/await
4. **单元素vs多元素**：`evaluate` 作用于第一个匹配元素，`evaluateAll` 作用于所有匹配元素
5. **错误传播**：函数中的错误会被适当包装和抛出