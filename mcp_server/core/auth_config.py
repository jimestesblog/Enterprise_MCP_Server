"""
JWT Authentication configuration management for MCP Server.

This module provides configuration models for JWT authentication
with support for OIDC-compliant identity providers including
Azure EntraID, AWS IAM, and other standard OIDC providers.
"""

import os
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator, HttpUrl
import yaml
import json


class JWTProviderConfig(BaseModel):
    """Configuration for a JWT identity provider."""
    
    # Provider identification
    name: str = Field(..., description="Provider name (e.g., azure-entraid, aws-iam, custom)")
    type: str = Field(..., description="Provider type: oidc, azure-entraid, aws-iam")
    
    # OIDC Discovery
    issuer: str = Field(..., description="JWT issuer URL")
    jwks_uri: Optional[str] = Field(None, description="JWKS endpoint URL (auto-discovered if not provided)")
    
    # Token validation settings
    audience: Union[str, List[str]] = Field(..., description="Expected audience(s) for token validation")
    algorithms: List[str] = Field(default=["RS256"], description="Allowed signing algorithms")
    
    # OIDC-specific settings
    userinfo_endpoint: Optional[str] = Field(None, description="UserInfo endpoint for additional claims")
    
    # Azure EntraID specific settings
    tenant_id: Optional[str] = Field(None, description="Azure tenant ID")
    
    # AWS IAM specific settings
    region: Optional[str] = Field(None, description="AWS region for IAM validation")
    
    # Token validation options
    verify_exp: bool = Field(default=True, description="Verify token expiration")
    verify_aud: bool = Field(default=True, description="Verify audience claim")
    verify_iss: bool = Field(default=True, description="Verify issuer claim")
    leeway: int = Field(default=0, description="Leeway for time-based claims in seconds")
    
    # Claims extraction
    subject_claim: str = Field(default="sub", description="Claim name for user subject")
    email_claim: str = Field(default="email", description="Claim name for user email")
    name_claim: str = Field(default="name", description="Claim name for user name")
    groups_claim: str = Field(default="groups", description="Claim name for user groups")
    roles_claim: str = Field(default="roles", description="Claim name for user roles")
    
    @validator('type')
    def validate_provider_type(cls, v):
        valid_types = ['oidc', 'azure-entraid', 'aws-iam']
        if v not in valid_types:
            raise ValueError(f'Provider type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('algorithms')
    def validate_algorithms(cls, v):
        if not v:
            raise ValueError('At least one algorithm must be specified')
        return v


class DomainAuthConfig(BaseModel):
    """Authentication configuration for a specific domain."""
    
    # Authentication settings
    enabled: bool = Field(default=False, description="Enable authentication for this domain")
    required: bool = Field(default=True, description="Require authentication (if enabled)")
    
    # Provider configuration
    provider: Optional[str] = Field(None, description="JWT provider name to use")
    
    # Authorization settings
    require_groups: List[str] = Field(default_factory=list, description="Required user groups")
    require_roles: List[str] = Field(default_factory=list, description="Required user roles")
    
    # Additional claims validation
    required_claims: Dict[str, Any] = Field(default_factory=dict, description="Additional required claims")
    
    @validator('provider')
    def validate_provider_required(cls, v, values):
        if values.get('enabled', False) and not v:
            raise ValueError('Provider must be specified when authentication is enabled')
        return v


class AuthConfig(BaseModel):
    """Main authentication configuration."""
    
    # Global authentication settings
    default_enabled: bool = Field(default=False, description="Default authentication state for new domains")
    
    # JWT providers
    providers: Dict[str, JWTProviderConfig] = Field(default_factory=dict, description="Available JWT providers")
    
    # Per-domain authentication configuration
    domains: Dict[str, DomainAuthConfig] = Field(default_factory=dict, description="Domain-specific auth configuration")
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


def expand_env_vars_auth(value: Any) -> Any:
    """Recursively expand environment variables in authentication configuration values."""
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value
    elif isinstance(value, dict):
        return {k: expand_env_vars_auth(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars_auth(item) for item in value]
    return value


def load_auth_config(path: Optional[str] = None) -> AuthConfig:
    """
    Load authentication configuration from file or return default config.
    
    Args:
        path: Optional path to authentication configuration file
        
    Returns:
        AuthConfig: Loaded and validated authentication configuration
    """
    if not path or not os.path.exists(path):
        return AuthConfig()
    
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f) or {}
        elif path.endswith(".json"):
            data = json.load(f)
        else:
            raise ValueError("Auth config file must be .yaml, .yml, or .json")
    
    # Expand environment variables
    data = expand_env_vars_auth(data)
    
    return AuthConfig(**data)


def get_default_auth_config_path() -> Optional[str]:
    """Get the default authentication configuration file path."""
    # Check environment variable first
    auth_config_path = os.getenv("AUTH_CONFIG_PATH")
    if auth_config_path and os.path.exists(auth_config_path):
        return auth_config_path
    
    # Check default location
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "auth.yaml"
    )
    if os.path.exists(default_path):
        return default_path
    
    return None