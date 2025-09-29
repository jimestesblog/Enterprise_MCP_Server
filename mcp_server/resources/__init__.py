"""
Resources module for MCP Server.

This module provides resource management capabilities for the MCP server,
supporting both public HTTP resources and internal MCP server resources.
"""

from .base import Resource, ResourceConfig, ResourceParameter
from .registry import ResourceRegistry, registry

__all__ = ["Resource", "ResourceConfig", "ResourceParameter", "ResourceRegistry", "registry"]