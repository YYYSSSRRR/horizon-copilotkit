# Changelog

All notable changes to the CopilotKit Python Runtime will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.15] - 2024-12-27

### Added
- Initial release of CopilotKit Python Runtime
- Core `CopilotRuntime` class with full TypeScript compatibility
- Support for multiple AI service adapters:
  - OpenAI Adapter
  - Anthropic Adapter
  - Google Gemini Adapter
  - DeepSeek Adapter
  - LangChain Adapter
- GraphQL API with Strawberry GraphQL
- FastAPI integration for easy deployment
- Event system for real-time streaming
- Middleware support for request/response processing
- Remote endpoint support for LangGraph Platform
- MCP (Model Context Protocol) support (experimental)
- Comprehensive type definitions with Pydantic
- Examples and documentation
- Unit tests with pytest

### Features
- 🚀 **完全兼容** - 与 TypeScript runtime 的 API 完全兼容
- 🔧 **多种适配器** - 支持 OpenAI、Anthropic、Google、DeepSeek、LangChain 等
- 🤖 **代理支持** - 支持 LangGraph、CrewAI 等代理框架
- 📊 **GraphQL API** - 提供完整的 GraphQL 接口
- 🔄 **流式响应** - 支持实时流式 AI 响应
- 🔗 **中间件系统** - 灵活的请求处理管道
- 🌐 **远程端点** - 支持 LangGraph Platform 等远程服务
- 🔧 **MCP 支持** - 模型上下文协议支持（实验性）

### Documentation
- Comprehensive README with usage examples
- API reference documentation
- Basic and advanced usage examples
- Migration guide from TypeScript version

### Development
- Poetry-based dependency management
- Black + isort for code formatting
- MyPy for type checking
- Ruff for linting
- Pytest for testing
- Makefile for development tasks 