# 代码风格和约定

## 代码格式化
- **Black**: 行长度88字符，目标Python 3.9
- **配置**: 使用 pyproject.toml 中的 [tool.black] 配置

## 类型提示
- **MyPy**: 严格类型检查
- 要求：
  - `disallow_untyped_defs = true` - 禁止未类型化的函数定义
  - `disallow_incomplete_defs = true` - 禁止不完整的类型定义
  - `check_untyped_defs = true` - 检查未类型化的函数
  - `disallow_untyped_decorators = true` - 禁止未类型化的装饰器
  - `no_implicit_optional = true` - 不隐式Optional

## 文档和注释
- 使用中文注释和docstring（从示例文件可看出）
- API文档应该清楚说明参数和返回值

## 命名约定
- 类名：PascalCase (如 `FunctionRAGClient`)
- 函数和变量：snake_case (如 `health_check`, `base_url`)
- 常量：UPPER_SNAKE_CASE

## 项目结构约定
- 使用相对导入在同一包内
- 服务层在 `app/services/`
- API路由在 `app/api/routes/`
- 数据模型在 `app/models/`
- 核心逻辑在 `app/core/`