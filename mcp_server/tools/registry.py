"""
Tool registry for MCP Server.

This module provides a simplified tool registration system
that replaces the complex tool factory pattern.
"""

import importlib
from typing import Dict, Type, Any, List
from ..core.exceptions import ToolRegistrationError
from .enhanced_base import Tool, ToolConfig


class ToolRegistry:
    """Registry for managing tool classes and instances."""
    
    _tools: Dict[str, Type[Tool]] = {}
    _instances: Dict[str, Tool] = {}
    
    @classmethod
    def register(cls, name: str, tool_class: Type[Tool]) -> None:
        """
        Register a tool class.
        
        Args:
            name: Tool name/identifier
            tool_class: Tool class to register
        """
        if not issubclass(tool_class, Tool):
            raise ToolRegistrationError(f"Tool class {tool_class} must inherit from Tool")
        
        cls._tools[name] = tool_class
    
    @classmethod
    def register_from_path(cls, name: str, class_path: str) -> None:
        """
        Register a tool class from a dotted import path.
        
        Args:
            name: Tool name/identifier
            class_path: Dotted path to tool class (e.g., 'package.module.Class')
        """
        tool_class = cls._import_from_path(class_path)
        cls.register(name, tool_class)
    
    @classmethod
    def create_tool(cls, name: str, config: ToolConfig) -> Tool:
        """
        Create a tool instance from registered class.
        
        Args:
            name: Tool name/identifier
            config: Tool configuration
            
        Returns:
            Tool instance
        """
        if name not in cls._tools:
            raise ToolRegistrationError(f"Unknown tool: {name}")
        
        tool_class = cls._tools[name]
        try:
            instance = tool_class(config)
            cls._instances[name] = instance
            return instance
        except Exception as e:
            raise ToolRegistrationError(f"Failed to create tool {name}: {str(e)}")
    
    @classmethod
    def get_tool(cls, name: str) -> Tool:
        """Get a tool instance by name."""
        if name not in cls._instances:
            raise ToolRegistrationError(f"Tool {name} not found or not created")
        return cls._instances[name]
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tool names."""
        return list(cls._tools.keys())
    
    @classmethod
    def list_instances(cls) -> List[str]:
        """List all created tool instance names."""
        return list(cls._instances.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools and instances."""
        cls._tools.clear()
        cls._instances.clear()
    
    @staticmethod
    def _import_from_path(path: str) -> Type[Tool]:
        """
        Import and return a tool class given a dotted path.
        
        Args:
            path: Dotted path like 'pkg.mod.Class'
            
        Returns:
            Tool class
        """
        module_name, _, attr = path.rpartition(".")
        if not module_name:
            raise ToolRegistrationError(f"Invalid class path: {path}")
        
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ToolRegistrationError(f"Cannot import module '{module_name}': {e}")
        
        try:
            tool_class = getattr(module, attr)
        except AttributeError:
            raise ToolRegistrationError(
                f"Cannot find attribute '{attr}' in module '{module_name}'"
            )
        
        if not issubclass(tool_class, Tool):
            raise ToolRegistrationError(
                f"Class {tool_class} must inherit from Tool"
            )
        
        return tool_class


# Global registry instance
registry = ToolRegistry()