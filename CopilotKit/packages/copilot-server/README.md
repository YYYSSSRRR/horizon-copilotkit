<div align="center">
  <a href="https://copilotkit.ai" target="_blank">
    <img src="https://github.com/copilotkit/copilotkit/raw/main/assets/banner.png" alt="CopilotKit Logo">
  </a>

  <br/>

  <strong>
    CopilotKit Runtime Python is the Python runtime for integrating powerful AI Copilots into any application. Easily implement custom AI Chatbots, AI Agents, AI Textareas, and more with Python backend support.
  </strong>
</div>

<br/>

<div align="center">
  <a href="https://pypi.org/project/copilotkit-runtime-python/" target="_blank">
    <img src="https://img.shields.io/pypi/v/copilotkit-runtime-python?logo=pypi&logoColor=%23FFFFFF&label=Version&color=%236963ff" alt="PyPI">
  </a>
  <img src="https://img.shields.io/github/license/copilotkit/copilotkit?color=%236963ff&label=License" alt="MIT">
  <a href="https://discord.gg/6dffbvGU3D" target="_blank">
    <img src="https://img.shields.io/discord/1122926057641742418?logo=discord&logoColor=%23FFFFFF&label=Discord&color=%236963ff" alt="Discord">
  </a>
</div>
<br/>

<div align="center">
  <a href="https://discord.gg/6dffbvGU3D?ref=github_readme" target="_blank">
    <img src="https://github.com/copilotkit/copilotkit/raw/main/assets/btn_discord.png" alt="CopilotKit Discord" height="40px">
  </a>
  <a href="https://docs.copilotkit.ai?ref=github_readme" target="_blank">
    <img src="https://github.com/copilotkit/copilotkit/raw/main/assets/btn_docs.png" alt="CopilotKit GitHub" height="40px">
  </a>
  <a href="https://cloud.copilotkit.ai?ref=github_readme" target="_blank">
    <img src="https://github.com/copilotkit/copilotkit/raw/main/assets/btn_cloud.png" alt="CopilotKit GitHub" height="40px">
  </a>
</div>

<br />

<div align="center">
  <img src="https://github.com/CopilotKit/CopilotKit/raw/main/assets/animated-banner.gif" alt="CopilotKit Screenshot" style="border-radius: 15px;" />
</div>

# CopilotKit Runtime Python

This package provides the Python runtime for CopilotKit, enabling seamless integration between Python-based AI services and CopilotKit's frontend components.

## Documentation

To get started with CopilotKit, please check out the [documentation](https://docs.copilotkit.ai).

## Features

- **Python Backend Support**: Full compatibility with Python-based AI frameworks and services
- **SSE Streaming**: Server-Sent Events for real-time streaming responses
- **DeepSeek Integration**: Specialized support for DeepSeek AI models
- **RxPy Integration**: Reactive programming with RxPy for event stream processing
- **FastAPI Integration**: Built-in FastAPI integration for rapid development
- **Real-time Streaming**: Live streaming of AI responses and events
- **Structured Logging**: Built-in logging with structlog
- **Type Safety**: Full type hints and mypy support

## Installation

```bash
pip install copilotkit-runtime-python
```

Or with Poetry:

```bash
poetry add copilotkit-runtime-python
```

## Quick Start

### Basic Usage

```python
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.service_adapters import DeepSeekAdapter
import os

# Create runtime with DeepSeek adapter
runtime = CopilotRuntime(
    adapter=DeepSeekAdapter(api_key=os.getenv("DEEPSEEK_API_KEY"))
)

# Use with FastAPI
from fastapi import FastAPI
from copilotkit_runtime.integrations import copilotkit_fastapi

app = FastAPI()
copilotkit_fastapi(app, runtime)
```

### Advanced Configuration

```python
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.service_adapters import DeepSeekAdapter
from copilotkit_runtime.logging import LoggingConfig

runtime = CopilotRuntime(
    adapter=DeepSeekAdapter(
        api_key="your-deepseek-key",
        model="deepseek-chat"
    ),
    logging=LoggingConfig(
        enabled=True,
        progressive=True,
        level="INFO"
    )
)
```

### DeepSeek Models

```python
from copilotkit_runtime.service_adapters import DeepSeekAdapter

# Configure DeepSeek adapter with different models
deepseek_chat_adapter = DeepSeekAdapter(
    api_key="deepseek-key",
    model="deepseek-chat"
)

deepseek_coder_adapter = DeepSeekAdapter(
    api_key="deepseek-key", 
    model="deepseek-coder"
)
```

## Service Adapters

CopilotKit Runtime Python focuses on DeepSeek AI integration:

- **DeepSeek Chat**: General conversation and reasoning models
- **DeepSeek Coder**: Specialized coding and programming models
- **Custom**: Build your own adapter extending the base adapter

## FastAPI Integration

```python
from fastapi import FastAPI
from copilotkit_runtime.integrations.fastapi import copilotkit_fastapi
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.service_adapters import DeepSeekAdapter

app = FastAPI()
runtime = CopilotRuntime(
    adapter=DeepSeekAdapter(api_key="your-key")
)

# Add CopilotKit endpoints to your FastAPI app
copilotkit_fastapi(app, runtime)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Custom Integration

```python
from copilotkit_runtime.service_adapters import ServiceAdapter
from copilotkit_runtime import CopilotRuntime

class CustomAdapter(ServiceAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def generate_response(self, messages, **kwargs):
        # Your custom implementation
        pass

adapter = CustomAdapter(api_key="your-key")
runtime = CopilotRuntime(adapter=adapter)
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/CopilotKit/CopilotKit.git
cd CopilotKit/packages/runtime-python

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=copilotkit_runtime

# Run specific test types
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black copilotkit_runtime tests

# Sort imports
isort copilotkit_runtime tests

# Lint code
flake8 copilotkit_runtime tests

# Type checking
mypy copilotkit_runtime
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](../../CONTRIBUTING.md) for more details.

## License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## Support

- 📚 [Documentation](https://docs.copilotkit.ai)
- 💬 [Discord Community](https://discord.gg/6dffbvGU3D)
- 🐛 [Issue Tracker](https://github.com/CopilotKit/CopilotKit/issues)
- 📧 [Email Support](mailto:support@copilotkit.ai)