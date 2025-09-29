"""
Custom exceptions for MCP Server.

This module defines the exception hierarchy used throughout
the MCP Server application.
"""

class MCPServerError(Exception):
    """Base exception for MCP Server."""
    pass


class ConfigurationError(MCPServerError):
    """Raised when configuration is invalid."""
    pass


class ToolExecutionError(MCPServerError):
    """Raised when tool execution fails."""
    
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ToolRegistrationError(MCPServerError):
    """Raised when tool registration fails."""
    pass


class ValidationError(MCPServerError):
    """Raised when parameter validation fails."""
    pass