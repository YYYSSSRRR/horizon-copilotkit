"""Logger implementation."""

import structlog
from typing import Any, Dict, Optional


class Logger:
    """Logger wrapper."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize logger."""
        self.name = name
        self.config = config or {}
        self._logger = structlog.get_logger(name)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def bind(self, **kwargs):
        """Bind additional context."""
        return Logger(self.name, self.config).with_logger(
            self._logger.bind(**kwargs)
        )
    
    def with_logger(self, logger):
        """Set the underlying logger."""
        self._logger = logger
        return self