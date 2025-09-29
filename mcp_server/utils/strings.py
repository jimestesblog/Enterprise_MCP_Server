"""
String utility functions for MCP Server.

This module contains string manipulation functions
used throughout the application.
"""

import re


def slugify(name: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    
    Args:
        name: Input string to slugify
        
    Returns:
        Slugified string
    """
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "default"


def normalize_parameter_name(name: str) -> str:
    """
    Normalize parameter names for consistency.
    
    Args:
        name: Parameter name to normalize
        
    Returns:
        Normalized parameter name
    """
    # Convert common variations to standard names
    name = name.strip().lower()
    
    # Handle coordinate variations
    if name in ["lat", "latitude"]:
        return "latitude"
    elif name in ["lon", "lng", "longitude"]:
        return "longitude"
    
    return name


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize a string value for safe use.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes and control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in ['\n', '\r', '\t'])
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length-3] + "..."
    
    return value.strip()