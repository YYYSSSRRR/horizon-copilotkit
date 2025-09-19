#!/usr/bin/env python3
"""Setup script for copilotkit-runtime-python."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="copilotkit-runtime-python",
    version="1.8.15",
    description="CopilotKit Python Runtime - The Python runtime for integrating powerful AI Copilots into any application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CopilotKit Team",
    author_email="team@copilotkit.ai",
    url="https://github.com/CopilotKit/CopilotKit",
    license="MIT",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8.1",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.5.0",
        "httpx>=0.25.0",
        "requests>=2.31.0",
        "reactivex>=4.0.4",
        "sse-starlette>=2.1.0",
        "structlog>=23.2.0",
        "aiohttp>=3.9.0",
        "typing-extensions>=4.8.0",
        "jsonschema>=4.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.12.0",
            "black>=23.10.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
            "pre-commit>=3.5.0",
            "coverage>=7.3.0",
            "pytest-cov>=4.1.0",
        ],
        "all": [
            "groq>=0.5.0",
            "google-generativeai>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "copilotkit-runtime=copilotkit_runtime.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Framework :: FastAPI",
    ],
    keywords="copilotkit copilot ai assistant python automation deepseek",
    project_urls={
        "Documentation": "https://docs.copilotkit.ai",
        "Source": "https://github.com/CopilotKit/CopilotKit",
        "Tracker": "https://github.com/CopilotKit/CopilotKit/issues",
        "Discord": "https://discord.gg/6dffbvGU3D",
    },
)