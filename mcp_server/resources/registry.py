"""
Resource registry for MCP Server.

This module provides a simplified resource registration system
following the same pattern as the tool registry.
"""

import importlib
from typing import Dict, Type, Any, List
from ..core.exceptions import ToolRegistrationError
from .base import Resource, ResourceConfig


class ResourceRegistrationError(Exception):
    """Exception raised when resource registration fails."""
    pass


class ResourceRegistry:
    """Registry for managing resource classes and instances."""
    
    _resources: Dict[str, Type[Resource]] = {}
    _instances: Dict[str, Resource] = {}
    
    @classmethod
    def register(cls, name: str, resource_class: Type[Resource]) -> None:
        """
        Register a resource class.
        
        Args:
            name: Resource name/identifier
            resource_class: Resource class to register
        """
        if not issubclass(resource_class, Resource):
            raise ResourceRegistrationError(f"Resource class {resource_class} must inherit from Resource")
        
        cls._resources[name] = resource_class
    
    @classmethod
    def register_from_path(cls, name: str, class_path: str) -> None:
        """
        Register a resource class from a dotted import path.
        
        Args:
            name: Resource name/identifier
            class_path: Dotted path to resource class (e.g., 'package.module.Class')
        """
        resource_class = cls._import_from_path(class_path)
        cls.register(name, resource_class)
    
    @classmethod
    def create_resource(cls, name: str, config: ResourceConfig) -> Resource:
        """
        Create a resource instance from registered class.
        
        Args:
            name: Resource name/identifier
            config: Resource configuration
            
        Returns:
            Resource instance
        """
        if name not in cls._resources:
            raise ResourceRegistrationError(f"Unknown resource: {name}")
        
        resource_class = cls._resources[name]
        try:
            instance = resource_class(config)
            cls._instances[name] = instance
            return instance
        except Exception as e:
            raise ResourceRegistrationError(f"Failed to create resource {name}: {str(e)}")
    
    @classmethod
    def get_resource(cls, name: str) -> Resource:
        """Get a resource instance by name."""
        if name not in cls._instances:
            raise ResourceRegistrationError(f"Resource {name} not found or not created")
        return cls._instances[name]
    
    @classmethod
    def list_resources(cls) -> List[str]:
        """List all registered resource names."""
        return list(cls._resources.keys())
    
    @classmethod
    def list_instances(cls) -> List[str]:
        """List all created resource instance names."""
        return list(cls._instances.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered resources and instances."""
        cls._resources.clear()
        cls._instances.clear()
    
    @staticmethod
    def _import_from_path(path: str) -> Type[Resource]:
        """
        Import and return a resource class given a dotted path.
        
        Args:
            path: Dotted path like 'pkg.mod.Class'
            
        Returns:
            Resource class
        """
        module_name, _, attr = path.rpartition(".")
        if not module_name:
            raise ResourceRegistrationError(f"Invalid class path: {path}")
        
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ResourceRegistrationError(f"Cannot import module '{module_name}': {e}")
        
        try:
            resource_class = getattr(module, attr)
        except AttributeError:
            raise ResourceRegistrationError(
                f"Cannot find attribute '{attr}' in module '{module_name}'"
            )
        
        if not issubclass(resource_class, Resource):
            raise ResourceRegistrationError(
                f"Class {resource_class} must inherit from Resource"
            )
        
        return resource_class


# Global registry instance
registry = ResourceRegistry()