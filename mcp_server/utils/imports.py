"""
Import utility functions for MCP Server.

This module contains functions for dynamic imports
and module loading.
"""

import importlib
from typing import Any, Type, Callable
from ..core.exceptions import ConfigurationError


def import_from_path(path: str) -> Any:
    """
    Import and return an attribute given a dotted path.
    
    Args:
        path: Dotted path like 'pkg.mod.Class'
        
    Returns:
        The imported attribute
        
    Raises:
        ConfigurationError: If import fails
    """
    module_name, _, attr = path.rpartition(".")
    if not module_name:
        raise ConfigurationError(f"Invalid import path: {path}")
    
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ConfigurationError(f"Cannot import module '{module_name}': {e}")
    
    try:
        return getattr(module, attr)
    except AttributeError:
        raise ConfigurationError(
            f"Cannot find attribute '{attr}' in module '{module_name}'"
        )


def safe_import(path: str, default: Any = None) -> Any:
    """
    Safely import an attribute, returning default if import fails.
    
    Args:
        path: Dotted path like 'pkg.mod.Class'
        default: Default value to return on failure
        
    Returns:
        The imported attribute or default value
    """
    try:
        return import_from_path(path)
    except ConfigurationError:
        return default


def is_importable(path: str) -> bool:
    """
    Check if a dotted path is importable.
    
    Args:
        path: Dotted path to check
        
    Returns:
        True if importable, False otherwise
    """
    try:
        import_from_path(path)
        return True
    except ConfigurationError:
        return False