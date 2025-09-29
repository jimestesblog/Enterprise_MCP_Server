"""
JSON Schema builders for MCP Server.

This module contains functions for building JSON schemas
from tool parameter definitions.
"""

from typing import Any, Dict, List


def infer_type_from_str(type_str: str) -> str:
    """
    Infer JSON schema type from string representation.
    
    Args:
        type_str: String representation of type
        
    Returns:
        JSON schema type string
    """
    s = str(type_str).strip().lower()
    if s in {"int", "integer"}:
        return "integer"
    if s in {"float", "number"}:
        return "number"
    if s in {"bool", "boolean"}:
        return "boolean"
    return "string"


def infer_type_from_enum_values(values: List[Any]) -> str:
    """
    Infer JSON schema type from enum values.
    
    Args:
        values: List of enum values
        
    Returns:
        JSON schema type string
    """
    if not values:
        return "string"
    
    # If all ints (excluding booleans)
    if all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        return "integer"
    
    # If any float -> number
    if any(isinstance(v, float) for v in values):
        return "number"
    
    # If all booleans
    if all(isinstance(v, bool) for v in values):
        return "boolean"
    
    # Otherwise strings
    return "string"


def build_schema_from_tool_parameters(params: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build JSON schema from tool parameter definitions.
    
    Args:
        params: List of parameter definitions
        
    Returns:
        JSON schema object
    """
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for p in params or []:
        if not isinstance(p, dict):
            continue
        
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        
        desc = p.get("description")
        allowed = p.get("allowed_values")
        schema: Dict[str, Any] = {}
        
        if isinstance(allowed, list):
            # enum constraint
            schema["enum"] = allowed
            schema["type"] = infer_type_from_enum_values(allowed)
        elif allowed is not None:
            schema["type"] = infer_type_from_str(str(allowed))
        
        # Description if provided
        if desc:
            schema["description"] = str(desc)
        
        # Required flag support
        if bool(p.get("required", False)):
            required.append(name)
        
        # Default to string type if no type specified
        if "type" not in schema and "enum" not in schema:
            schema["type"] = "string"
        
        properties[name] = schema

    schema_obj: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        # Keep permissive to avoid breaking backward compatibility
        "additionalProperties": True,
    }
    
    if required:
        schema_obj["required"] = required
    
    return schema_obj


def create_basic_schema(required_fields: List[str] = None, 
                       optional_fields: List[str] = None) -> Dict[str, Any]:
    """
    Create a basic JSON schema with specified fields.
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names
        
    Returns:
        JSON schema object
    """
    properties = {}
    
    for field in required_fields or []:
        properties[field] = {"type": "string"}
    
    for field in optional_fields or []:
        properties[field] = {"type": "string"}
    
    schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": True
    }
    
    if required_fields:
        schema["required"] = required_fields
    
    return schema