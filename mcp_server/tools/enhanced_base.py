"""
Enhanced base classes for MCP Server tools.

This module provides improved abstract base classes with proper
typing and configuration management using Pydantic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Typed configuration for tools."""
    name: str = Field(..., description="Tool name")
    description: str = Field("", description="Tool description")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    
    class Config:
        extra = "allow"  # Allow additional fields for tool-specific config


class Tool(ABC):
    """Enhanced abstract base class for all tools."""
    
    def __init__(self, config: ToolConfig):
        self.config = config
        self.name = config.name
        self.description = config.description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters."""
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        # Default implementation - tools can override
        return params
    
    def to_mcp_def(self) -> Dict[str, Any]:
        """Convert to MCP tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_schema()
        }

