"""
JWT Authentication middleware for MCP Server domains.

This module provides FastAPI middleware for JWT token validation
that can be applied per domain based on authentication configuration.
"""

import logging
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .auth_config import AuthConfig, DomainAuthConfig, JWTProviderConfig
from .auth_validator import JWTValidatorFactory, DomainAuthenticator, JWTValidationError, SecurityContext

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware for FastAPI applications."""
    
    def __init__(self, app, auth_config: AuthConfig, domain_name: str):
        """
        Initialize JWT authentication middleware for a specific domain.
        
        Args:
            app: FastAPI application instance
            auth_config: Authentication configuration
            domain_name: Name of the domain this middleware protects
        """
        super().__init__(app)
        self.auth_config = auth_config
        self.domain_name = domain_name
        self.domain_auth_config = auth_config.domains.get(domain_name)
        self.authenticator: Optional[DomainAuthenticator] = None
        
        # Initialize authenticator if authentication is enabled for this domain
        if self.domain_auth_config and self.domain_auth_config.enabled:
            self._initialize_authenticator()
    
    def _initialize_authenticator(self):
        """Initialize the domain authenticator."""
        try:
            if not self.domain_auth_config or not self.domain_auth_config.provider:
                logger.error(f"No provider configured for domain {self.domain_name}")
                return
            
            provider_config = self.auth_config.providers.get(self.domain_auth_config.provider)
            if not provider_config:
                logger.error(f"Provider {self.domain_auth_config.provider} not found for domain {self.domain_name}")
                return
            
            validator = JWTValidatorFactory.create_validator(provider_config)
            self.authenticator = DomainAuthenticator(self.domain_auth_config, validator)
            
            logger.info(f"Authentication enabled for domain {self.domain_name} with provider {self.domain_auth_config.provider}")
            
        except Exception as e:
            logger.error(f"Failed to initialize authenticator for domain {self.domain_name}: {e}")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request through authentication middleware.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        # Skip authentication if not enabled or configured
        if not self.authenticator or not self.domain_auth_config or not self.domain_auth_config.enabled:
            return await call_next(request)
        
        # Skip authentication for health checks and other non-protected endpoints
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        try:
            # Extract and validate JWT token
            token = self._extract_token(request)
            if not token:
                if self.domain_auth_config.required:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    # Authentication not required, continue without context
                    return await call_next(request)
            
            # Authenticate and authorize request
            security_context = await self.authenticator.authenticate_request(token)
            
            # Add security context to request state
            request.state.security_context = security_context
            request.state.authenticated = True
            
            logger.debug(f"Authenticated user {security_context.subject} for domain {self.domain_name}")
            
        except JWTValidationError as e:
            logger.warning(f"Authentication failed for domain {self.domain_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Authentication error for domain {self.domain_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
        
        return await call_next(request)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request.
        
        Args:
            request: HTTP request
            
        Returns:
            JWT token string or None
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Try query parameter (less secure, but sometimes needed)
        token_param = request.query_params.get("token")
        if token_param:
            return token_param
        
        return None
    
    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authentication should be skipped for a given path.
        
        Args:
            path: Request path
            
        Returns:
            True if authentication should be skipped
        """
        skip_paths = [
            "/healthz",
            "/readyz", 
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)


class AuthenticationManager:
    """Manager for handling authentication across multiple domains."""
    
    def __init__(self, auth_config: AuthConfig):
        """
        Initialize authentication manager.
        
        Args:
            auth_config: Authentication configuration
        """
        self.auth_config = auth_config
        self._authenticators: Dict[str, DomainAuthenticator] = {}
    
    def get_domain_authenticator(self, domain_name: str) -> Optional[DomainAuthenticator]:
        """
        Get authenticator for a specific domain.
        
        Args:
            domain_name: Domain name
            
        Returns:
            Domain authenticator or None if not configured
        """
        if domain_name in self._authenticators:
            return self._authenticators[domain_name]
        
        domain_config = self.auth_config.domains.get(domain_name)
        if not domain_config or not domain_config.enabled:
            return None
        
        try:
            provider_config = self.auth_config.providers.get(domain_config.provider)
            if not provider_config:
                logger.error(f"Provider {domain_config.provider} not found for domain {domain_name}")
                return None
            
            validator = JWTValidatorFactory.create_validator(provider_config)
            authenticator = DomainAuthenticator(domain_config, validator)
            self._authenticators[domain_name] = authenticator
            
            return authenticator
            
        except Exception as e:
            logger.error(f"Failed to create authenticator for domain {domain_name}: {e}")
            return None
    
    def is_authentication_enabled(self, domain_name: str) -> bool:
        """
        Check if authentication is enabled for a domain.
        
        Args:
            domain_name: Domain name
            
        Returns:
            True if authentication is enabled
        """
        domain_config = self.auth_config.domains.get(domain_name)
        return domain_config is not None and domain_config.enabled
    
    def create_middleware(self, app, domain_name: str) -> JWTAuthenticationMiddleware:
        """
        Create authentication middleware for a domain.
        
        Args:
            app: FastAPI application
            domain_name: Domain name
            
        Returns:
            JWT authentication middleware
        """
        return JWTAuthenticationMiddleware(app, self.auth_config, domain_name)


# Dependency for getting security context in FastAPI endpoints
def get_security_context(request: Request) -> Optional[SecurityContext]:
    """
    FastAPI dependency to get security context from authenticated request.
    
    Args:
        request: HTTP request
        
    Returns:
        Security context or None if not authenticated
    """
    return getattr(request.state, 'security_context', None)


def require_authentication(request: Request) -> SecurityContext:
    """
    FastAPI dependency that requires authentication.
    
    Args:
        request: HTTP request
        
    Returns:
        Security context
        
    Raises:
        HTTPException: If not authenticated
    """
    security_context = get_security_context(request)
    if not security_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return security_context


def require_groups(*required_groups: str):
    """
    FastAPI dependency factory that requires specific groups.
    
    Args:
        required_groups: Required group names
        
    Returns:
        FastAPI dependency function
    """
    def dependency(request: Request) -> SecurityContext:
        security_context = require_authentication(request)
        
        if not security_context.has_any_group(list(required_groups)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of groups: {', '.join(required_groups)}"
            )
        
        return security_context
    
    return dependency


def require_roles(*required_roles: str):
    """
    FastAPI dependency factory that requires specific roles.
    
    Args:
        required_roles: Required role names
        
    Returns:
        FastAPI dependency function
    """
    def dependency(request: Request) -> SecurityContext:
        security_context = require_authentication(request)
        
        if not security_context.has_any_role(list(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of roles: {', '.join(required_roles)}"
            )
        
        return security_context
    
    return dependency