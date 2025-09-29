"""
JWT Token validation and security context management for MCP Server.

This module provides JWT token validation with support for OIDC-compliant
identity providers including Azure EntraID, AWS IAM, and standard OIDC providers.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging

import jwt
from jwt import PyJWKClient, decode, InvalidTokenError, ExpiredSignatureError
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .auth_config import JWTProviderConfig, DomainAuthConfig

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context extracted from validated JWT token."""
    
    # User identification
    subject: str
    email: Optional[str] = None
    name: Optional[str] = None
    
    # Authorization
    groups: List[str] = None
    roles: List[str] = None
    
    # Token metadata
    issuer: str = None
    audience: Union[str, List[str]] = None
    expires_at: Optional[int] = None
    issued_at: Optional[int] = None
    
    # Raw claims
    claims: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.roles is None:
            self.roles = []
        if self.claims is None:
            self.claims = {}
    
    def has_group(self, group: str) -> bool:
        """Check if user belongs to a specific group."""
        return group in self.groups
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_group(self, groups: List[str]) -> bool:
        """Check if user belongs to any of the specified groups."""
        return any(group in self.groups for group in groups)
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


class JWTValidationError(Exception):
    """Exception raised during JWT validation."""
    pass


class JWTValidator:
    """Base JWT token validator."""
    
    def __init__(self, provider_config: JWTProviderConfig):
        self.config = provider_config
        self._jwks_client: Optional[PyJWKClient] = None
        self._oidc_config: Optional[Dict[str, Any]] = None
        self._last_discovery = 0
        self._discovery_cache_ttl = 3600  # 1 hour
    
    async def validate_token(self, token: str) -> SecurityContext:
        """
        Validate JWT token and extract security context.
        
        Args:
            token: JWT token string
            
        Returns:
            SecurityContext: Extracted security context
            
        Raises:
            JWTValidationError: If token validation fails
        """
        try:
            # Ensure OIDC configuration is loaded
            await self._ensure_oidc_config()
            
            # Decode and validate token
            payload = await self._decode_token(token)
            
            # Extract security context
            return self._extract_security_context(payload)
            
        except Exception as e:
            logger.error(f"JWT validation failed: {e}")
            raise JWTValidationError(f"Token validation failed: {str(e)}")
    
    async def _ensure_oidc_config(self):
        """Ensure OIDC configuration is loaded and cached."""
        current_time = time.time()
        if (self._oidc_config is None or 
            current_time - self._last_discovery > self._discovery_cache_ttl):
            await self._discover_oidc_config()
            self._last_discovery = current_time
    
    async def _discover_oidc_config(self):
        """Discover OIDC configuration from provider."""
        try:
            # Standard OIDC discovery endpoint
            discovery_url = f"{self.config.issuer.rstrip('/')}/.well-known/openid_configuration"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                self._oidc_config = response.json()
                
            # Initialize JWKS client
            jwks_uri = self.config.jwks_uri or self._oidc_config.get('jwks_uri')
            if jwks_uri:
                self._jwks_client = PyJWKClient(jwks_uri)
            else:
                raise JWTValidationError("No JWKS URI available")
                
        except Exception as e:
            logger.error(f"OIDC discovery failed for {self.config.issuer}: {e}")
            raise JWTValidationError(f"OIDC discovery failed: {str(e)}")
    
    async def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token."""
        try:
            # Get signing key
            signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            
            # Decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.config.algorithms,
                audience=self.config.audience if self.config.verify_aud else None,
                issuer=self.config.issuer if self.config.verify_iss else None,
                options={
                    "verify_exp": self.config.verify_exp,
                    "verify_aud": self.config.verify_aud,
                    "verify_iss": self.config.verify_iss,
                },
                leeway=self.config.leeway
            )
            
            return payload
            
        except ExpiredSignatureError:
            raise JWTValidationError("Token has expired")
        except InvalidTokenError as e:
            raise JWTValidationError(f"Invalid token: {str(e)}")
    
    def _extract_security_context(self, payload: Dict[str, Any]) -> SecurityContext:
        """Extract security context from JWT payload."""
        return SecurityContext(
            subject=payload.get(self.config.subject_claim),
            email=payload.get(self.config.email_claim),
            name=payload.get(self.config.name_claim),
            groups=payload.get(self.config.groups_claim, []),
            roles=payload.get(self.config.roles_claim, []),
            issuer=payload.get('iss'),
            audience=payload.get('aud'),
            expires_at=payload.get('exp'),
            issued_at=payload.get('iat'),
            claims=payload
        )


class AzureEntraIDValidator(JWTValidator):
    """Azure EntraID specific JWT validator."""
    
    async def _discover_oidc_config(self):
        """Azure EntraID specific OIDC discovery."""
        try:
            tenant_id = self.config.tenant_id
            if not tenant_id:
                # Try to extract tenant from issuer
                if '/v2.0' in self.config.issuer:
                    parts = self.config.issuer.split('/')
                    tenant_idx = parts.index('v2.0') - 1
                    if tenant_idx >= 0:
                        tenant_id = parts[tenant_idx]
            
            if not tenant_id:
                raise JWTValidationError("Azure tenant ID not found")
            
            # Azure v2.0 endpoint
            discovery_url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid_configuration"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                self._oidc_config = response.json()
            
            # Initialize JWKS client
            jwks_uri = self.config.jwks_uri or self._oidc_config.get('jwks_uri')
            if jwks_uri:
                self._jwks_client = PyJWKClient(jwks_uri)
            else:
                raise JWTValidationError("No JWKS URI available for Azure EntraID")
                
        except Exception as e:
            logger.error(f"Azure EntraID discovery failed: {e}")
            raise JWTValidationError(f"Azure EntraID discovery failed: {str(e)}")
    
    def _extract_security_context(self, payload: Dict[str, Any]) -> SecurityContext:
        """Extract security context with Azure-specific claims."""
        context = super()._extract_security_context(payload)
        
        # Azure-specific group and role handling
        if 'groups' in payload:
            context.groups = payload['groups']
        elif 'roles' in payload:
            # Azure sometimes uses 'roles' for groups
            context.groups = payload['roles']
        
        # Handle Azure app roles
        if 'roles' in payload:
            context.roles = payload['roles']
        
        return context


class AWSIAMValidator(JWTValidator):
    """AWS IAM specific JWT validator."""
    
    async def _discover_oidc_config(self):
        """AWS IAM specific OIDC discovery."""
        try:
            region = self.config.region or 'us-east-1'
            
            # AWS OIDC discovery for IAM roles
            if 'oidc.eks' in self.config.issuer:
                # EKS OIDC provider
                discovery_url = f"{self.config.issuer}/.well-known/openid_configuration"
            else:
                # Standard AWS OIDC
                discovery_url = f"{self.config.issuer}/.well-known/openid_configuration"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                self._oidc_config = response.json()
            
            # Initialize JWKS client
            jwks_uri = self.config.jwks_uri or self._oidc_config.get('jwks_uri')
            if jwks_uri:
                self._jwks_client = PyJWKClient(jwks_uri)
            else:
                raise JWTValidationError("No JWKS URI available for AWS IAM")
                
        except Exception as e:
            logger.error(f"AWS IAM discovery failed: {e}")
            raise JWTValidationError(f"AWS IAM discovery failed: {str(e)}")
    
    def _extract_security_context(self, payload: Dict[str, Any]) -> SecurityContext:
        """Extract security context with AWS-specific claims."""
        context = super()._extract_security_context(payload)
        
        # AWS-specific role handling
        if 'aws:roles' in payload:
            context.roles = payload['aws:roles']
        elif 'https://aws.amazon.com/tags' in payload:
            # Extract roles from AWS tags
            aws_tags = payload['https://aws.amazon.com/tags']
            if isinstance(aws_tags, dict) and 'Role' in aws_tags:
                context.roles = [aws_tags['Role']]
        
        return context


class JWTValidatorFactory:
    """Factory for creating JWT validators based on provider type."""
    
    @staticmethod
    def create_validator(provider_config: JWTProviderConfig) -> JWTValidator:
        """
        Create appropriate JWT validator based on provider type.
        
        Args:
            provider_config: JWT provider configuration
            
        Returns:
            JWTValidator: Appropriate validator instance
        """
        if provider_config.type == 'azure-entraid':
            return AzureEntraIDValidator(provider_config)
        elif provider_config.type == 'aws-iam':
            return AWSIAMValidator(provider_config)
        else:
            return JWTValidator(provider_config)


class DomainAuthenticator:
    """Domain-specific authentication handler."""
    
    def __init__(self, domain_config: DomainAuthConfig, validator: JWTValidator):
        self.domain_config = domain_config
        self.validator = validator
    
    async def authenticate_request(self, token: str) -> SecurityContext:
        """
        Authenticate request and validate authorization.
        
        Args:
            token: JWT token string
            
        Returns:
            SecurityContext: Validated security context
            
        Raises:
            JWTValidationError: If authentication or authorization fails
        """
        # Validate token
        context = await self.validator.validate_token(token)
        
        # Check authorization requirements
        if not self._check_authorization(context):
            raise JWTValidationError("Access denied: insufficient permissions")
        
        return context
    
    def _check_authorization(self, context: SecurityContext) -> bool:
        """Check if security context meets domain authorization requirements."""
        # Check required groups
        if self.domain_config.require_groups:
            if not context.has_any_group(self.domain_config.require_groups):
                return False
        
        # Check required roles
        if self.domain_config.require_roles:
            if not context.has_any_role(self.domain_config.require_roles):
                return False
        
        # Check additional required claims
        if self.domain_config.required_claims:
            for claim_name, required_value in self.domain_config.required_claims.items():
                if context.claims.get(claim_name) != required_value:
                    return False
        
        return True