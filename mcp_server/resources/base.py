"""
Base classes for MCP Server resources.

This module provides abstract base classes with proper typing and 
configuration management for resources using Pydantic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum


class ResourceAccessType(str, Enum):
    """Resource access types."""
    PUBLIC = "public"
    MCP_SERVER = "mcp_server"


class ResourceParameter(BaseModel):
    """Configuration for resource parameters."""
    name: str = Field(..., description="Parameter name")
    description: str = Field("", description="Parameter description")
    allowed_values: Union[str, List[str]] = Field(default="string", description="Allowed parameter values")
    
    class Config:
        extra = "allow"


class ResourceConfig(BaseModel):
    """Typed configuration for resources."""
    name: str = Field(..., description="Resource name")
    description: str = Field("", description="Resource description")
    type: str = Field(..., description="Resource type (e.g., csv, txt, json)")
    access: ResourceAccessType = Field(..., description="Resource access type")
    uri: str = Field(..., description="Resource URI (may contain parameters)")
    function: Optional[str] = Field(None, description="Function name for mcp_server resources")
    resource_parameters: List[ResourceParameter] = Field(default_factory=list, description="Resource parameters")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional resource parameters")
    
    class Config:
        extra = "allow"  # Allow additional fields for resource-specific config
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Return JSON schema for resource parameters."""
        if not self.resource_parameters:
            return {"type": "object", "properties": {}}
        
        properties = {}
        required = []
        
        for param in self.resource_parameters:
            param_schema = {"description": param.description}
            
            if isinstance(param.allowed_values, str):
                if param.allowed_values == "string":
                    param_schema["type"] = "string"
                elif param.allowed_values == "number":
                    param_schema["type"] = "number"
                elif param.allowed_values == "boolean":
                    param_schema["type"] = "boolean"
                else:
                    param_schema["type"] = "string"
            elif isinstance(param.allowed_values, list):
                param_schema["type"] = "string"
                param_schema["enum"] = param.allowed_values
            
            properties[param.name] = param_schema
            required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def to_mcp_def(self) -> Dict[str, Any]:
        """Convert to MCP resource definition."""
        resource_def = {
            "name": self.name,
            "description": self.description,
            "uri": self.uri,
            "mimeType": self._get_mime_type()
        }
        
        if self.resource_parameters:
            resource_def["parameters"] = self.get_parameter_schema()
        
        return resource_def
    
    def _get_mime_type(self) -> str:
        """Get MIME type based on resource type."""
        mime_types = {
            "csv": "text/csv",
            "txt": "text/plain",
            "json": "application/json",
            "xml": "application/xml",
            "html": "text/html",
            "pdf": "application/pdf"
        }
        return mime_types.get(self.type.lower(), "text/plain")


class Resource(ABC):
    """Abstract base class for all resources."""
    
    def __init__(self, config: ResourceConfig):
        self.config = config
        self.name = config.name
        self.description = config.description
        self.type = config.type
        self.access = config.access
        self.uri = config.uri
        self.function = config.function
        self.resource_parameters = config.resource_parameters
    
    @abstractmethod
    async def get_content(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Get the resource content."""
        pass
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Return JSON schema for resource parameters."""
        if not self.resource_parameters:
            return {"type": "object", "properties": {}}
        
        properties = {}
        required = []
        
        for param in self.resource_parameters:
            param_schema = {"description": param.description}
            
            if isinstance(param.allowed_values, str):
                if param.allowed_values == "string":
                    param_schema["type"] = "string"
                elif param.allowed_values == "number":
                    param_schema["type"] = "number"
                elif param.allowed_values == "boolean":
                    param_schema["type"] = "boolean"
                else:
                    param_schema["type"] = "string"
            elif isinstance(param.allowed_values, list):
                param_schema["type"] = "string"
                param_schema["enum"] = param.allowed_values
            
            properties[param.name] = param_schema
            required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        # Default implementation - resources can override
        return parameters or {}
    
    def substitute_parameters(self, uri: str, parameters: Dict[str, Any]) -> str:
        """Substitute parameters in URI template."""
        result = uri
        for key, value in parameters.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def to_mcp_def(self) -> Dict[str, Any]:
        """Convert to MCP resource definition."""
        resource_def = {
            "name": self.name,
            "description": self.description,
            "uri": self.uri,
            "mimeType": self._get_mime_type()
        }
        
        if self.resource_parameters:
            resource_def["parameters"] = self.get_parameter_schema()
        
        return resource_def
    
    def _get_mime_type(self) -> str:
        """Get MIME type based on resource type."""
        mime_types = {
            "csv": "text/csv",
            "txt": "text/plain",
            "json": "application/json",
            "xml": "application/xml",
            "html": "text/html",
            "pdf": "application/pdf"
        }
        return mime_types.get(self.type.lower(), "text/plain")