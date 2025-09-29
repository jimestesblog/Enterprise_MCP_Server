"""
Configuration management for MCP Server.

This module provides centralized configuration handling using Pydantic
with support for environment variables and secure API key management.
"""

import os
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import yaml
import json


class DomainConfig(BaseModel):
    """Configuration for a domain."""
    name: str = Field(..., description="Domain name")
    description: str = Field("", description="Domain description")


class ToolConfig(BaseModel):
    """Configuration for a tool."""
    name: str = Field(..., description="Tool name")
    class_type: str = Field(..., description="Full class path")
    domain: str = Field("default", description="Domain name")
    description: str = Field("", description="Tool description")
    initialization_params: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('class_type')
    def validate_class_type(cls, v):
        if not v or '.' not in v:
            raise ValueError('class_type must be a valid dotted path')
        return v


class ResourceParameterConfig(BaseModel):
    """Configuration for a resource parameter."""
    name: str = Field(..., description="Parameter name")
    description: str = Field("", description="Parameter description")
    allowed_values: Union[str, List[str]] = Field(default="string", description="Allowed parameter values")


class ResourceConfig(BaseModel):
    """Configuration for a resource."""
    name: str = Field(..., description="Resource name")
    description: str = Field("", description="Resource description")
    type: str = Field(..., description="Resource type (e.g., csv, txt, json)")
    access: str = Field(..., description="Resource access type (public or mcp_server)")
    uri: str = Field(..., description="Resource URI (may contain parameters)")
    function: Optional[str] = Field(None, description="Function name for mcp_server resources")
    resource_parameters: List[ResourceParameterConfig] = Field(default_factory=list, description="Resource parameters")


class ResourceClassConfig(BaseModel):
    """Configuration for a resource class."""
    name: str = Field(..., description="Resource class name")
    class_type: str = Field(..., description="Full class path")
    domain: str = Field("default", description="Domain name")
    description: str = Field("", description="Resource class description")
    initialization_params: Dict[str, Any] = Field(default_factory=dict)
    resources: List[ResourceConfig] = Field(default_factory=list, description="Resources managed by this class")
    
    @validator('class_type')
    def validate_class_type(cls, v):
        if not v or '.' not in v:
            raise ValueError('class_type must be a valid dotted path')
        return v


class AppConfig(BaseModel):
    """Main application configuration."""
    domains: List[DomainConfig] = Field(default_factory=list)
    tools: List[ToolConfig] = Field(default_factory=list)
    resources: List[ResourceClassConfig] = Field(default_factory=list)
    
    # Legacy support for existing config format
    Domains: Optional[List[Dict[str, Any]]] = None
    mcp_classes: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


def expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in configuration values."""
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def load_config(path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from file or return default config.
    
    Args:
        path: Optional path to configuration file
        
    Returns:
        AppConfig: Loaded and validated configuration
    """
    if not path or not os.path.exists(path):
        return AppConfig()
    
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f) or {}
        elif path.endswith(".json"):
            data = json.load(f)
        else:
            raise ValueError("Config file must be .yaml, .yml, or .json")
    
    # Expand environment variables
    data = expand_env_vars(data)
    
    # Convert legacy format to new format if needed
    if "Domains" in data and not data.get("domains"):
        domains = []
        for domain_data in data.get("Domains", []):
            domains.append(DomainConfig(
                name=domain_data.get("Name", "default"),
                description=domain_data.get("Description", "")
            ))
        data["domains"] = domains
    
    if "mcp_classes" in data and not data.get("tools"):
        tools = []
        resources = []
        for tool_data in data.get("mcp_classes", []):
            # Check if this class has resources
            if "resources" in tool_data:
                # Convert to resource class config
                resource_configs = []
                for res_data in tool_data.get("resources", []):
                    # Convert resource parameters
                    res_params = []
                    for param in res_data.get("resource_parameters", []):
                        res_params.append(ResourceParameterConfig(**param))
                    
                    resource_configs.append(ResourceConfig(
                        name=res_data["name"],
                        description=res_data["description"],
                        type=res_data["type"],
                        access=res_data["access"],
                        uri=res_data["uri"],
                        function=res_data.get("function"),
                        resource_parameters=res_params
                    ))
                
                resources.append(ResourceClassConfig(
                    name=tool_data.get("class_name", "resource"),
                    class_type=tool_data.get("class_type", ""),
                    domain=tool_data.get("Domain", "default"),
                    description=tool_data.get("class_description", ""),
                    initialization_params=tool_data.get("class_initialization_params", {}),
                    resources=resource_configs
                ))
            else:
                # Regular tool config
                tools.append(ToolConfig(
                    name=tool_data.get("class_name", "tool"),
                    class_type=tool_data.get("class_type", ""),
                    domain=tool_data.get("Domain", "default"),
                    description=tool_data.get("class_description", ""),
                    initialization_params=tool_data.get("class_initialization_params", {})
                ))
        data["tools"] = tools
        data["resources"] = resources
    
    return AppConfig(**data)


def get_default_config_path() -> Optional[str]:
    """Get the default configuration file path."""
    # Check environment variable first
    config_path = os.getenv("CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        return config_path
    
    # Check default location
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "tools.yaml"
    )
    if os.path.exists(default_path):
        return default_path
    
    return None