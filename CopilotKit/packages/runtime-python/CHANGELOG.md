# Changelog

All notable changes to the CopilotKit Runtime Python package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.15-next.0] - 2024-01-15

### Added
- Initial release of CopilotKit Runtime Python
- Core runtime functionality with Python support
- Multiple AI service adapters (OpenAI, Anthropic, DeepSeek, Google, Groq)
- FastAPI integration for web applications
- LangChain and LangGraph integration
- GraphQL schema and resolvers with Strawberry
- Streaming support for real-time AI responses
- Comprehensive logging and observability
- Type safety with full mypy support
- Unit and integration test framework
- Documentation and examples

### Features
- **Service Adapters**: Specialized support for DeepSeek AI
  - DeepSeek Chat (General conversation and reasoning)
  - DeepSeek Coder (Specialized coding and programming)
  - Custom adapter framework for extensibility
  
- **Integrations**: 
  - FastAPI web framework integration with SSE support
  - RxPy reactive programming for event streams
  - Custom integration framework
  
- **Runtime Features**:
  - Real-time streaming responses
  - Custom action support
  - Agent state management
  - Error handling and recovery
  - Progressive and buffered logging
  
- **Developer Experience**:
  - Full type hints and mypy support
  - Comprehensive test suite
  - Black code formatting
  - Poetry dependency management
  - Pre-commit hooks for code quality

### Dependencies
- fastapi>=0.104.0
- uvicorn>=0.24.0
- pydantic>=2.5.0
- httpx>=0.25.0
- requests>=2.31.0
- strawberry-graphql>=0.215.0
- aiohttp>=3.9.0
- typing-extensions>=4.8.0