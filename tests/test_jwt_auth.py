"""
Test cases for JWT authentication functionality.

Tests JWT token validation, domain-specific authentication,
and OIDC compliance for the MCP server.
"""

import pytest
import jwt
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from mcp_server.core.auth_config import JWTProviderConfig, DomainAuthConfig, AuthConfig
from mcp_server.core.auth_validator import (
    JWTValidator, AzureEntraIDValidator, AWSIAMValidator,
    JWTValidatorFactory, DomainAuthenticator, SecurityContext,
    JWTValidationError
)
from mcp_server.core.auth_middleware import (
    JWTAuthenticationMiddleware, AuthenticationManager,
    get_security_context, require_authentication
)


# Test fixtures
@pytest.fixture
def rsa_key_pair():
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_key, public_key, private_pem, public_pem


@pytest.fixture
def test_jwt_token(rsa_key_pair):
    """Create a test JWT token."""
    private_key, _, _, _ = rsa_key_pair
    
    payload = {
        "sub": "test-user",
        "email": "test@example.com",
        "name": "Test User",
        "groups": ["users", "weather-users"],
        "roles": ["user", "viewer"],
        "iss": "https://test-issuer.com",
        "aud": "test-audience",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token, payload


@pytest.fixture
def mock_jwks_response():
    """Mock JWKS response."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-key-id",
                "n": "mock-n-value",
                "e": "AQAB"
            }
        ]
    }


@pytest.fixture
def mock_oidc_config():
    """Mock OIDC configuration response."""
    return {
        "issuer": "https://test-issuer.com",
        "jwks_uri": "https://test-issuer.com/.well-known/jwks.json",
        "authorization_endpoint": "https://test-issuer.com/auth",
        "token_endpoint": "https://test-issuer.com/token",
        "userinfo_endpoint": "https://test-issuer.com/userinfo"
    }


@pytest.fixture
def jwt_provider_config():
    """Test JWT provider configuration."""
    return JWTProviderConfig(
        name="test-provider",
        type="oidc",
        issuer="https://test-issuer.com",
        audience="test-audience",
        algorithms=["RS256"]
    )


@pytest.fixture
def domain_auth_config():
    """Test domain authentication configuration."""
    return DomainAuthConfig(
        enabled=True,
        required=True,
        provider="test-provider",
        require_groups=["users"],
        require_roles=["viewer"]
    )


@pytest.fixture
def auth_config(jwt_provider_config, domain_auth_config):
    """Test authentication configuration."""
    return AuthConfig(
        providers={"test-provider": jwt_provider_config},
        domains={"TEST_DOMAIN": domain_auth_config}
    )


# Test JWT Validator
class TestJWTValidator:
    """Test JWT token validation."""
    
    @pytest.mark.asyncio
    async def test_jwt_validator_initialization(self, jwt_provider_config):
        """Test JWT validator initialization."""
        validator = JWTValidator(jwt_provider_config)
        assert validator.config == jwt_provider_config
        assert validator._jwks_client is None
        assert validator._oidc_config is None
    
    @pytest.mark.asyncio
    async def test_security_context_creation(self):
        """Test security context creation and methods."""
        context = SecurityContext(
            subject="test-user",
            email="test@example.com",
            groups=["users", "admins"],
            roles=["viewer", "editor"],
            claims={"custom": "value"}
        )
        
        assert context.subject == "test-user"
        assert context.has_group("users")
        assert context.has_role("viewer")
        assert context.has_any_group(["users", "unknown"])
        assert context.has_any_role(["viewer", "unknown"])
        assert not context.has_group("unknown")
        assert not context.has_role("unknown")
    
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_oidc_discovery(self, mock_client, jwt_provider_config, mock_oidc_config):
        """Test OIDC configuration discovery."""
        mock_response = Mock()
        mock_response.json.return_value = mock_oidc_config
        mock_response.raise_for_status = Mock()
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        validator = JWTValidator(jwt_provider_config)
        await validator._discover_oidc_config()
        
        assert validator._oidc_config == mock_oidc_config
    
    @patch('jwt.PyJWKClient')
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_token_validation_success(self, mock_client, mock_jwks_client, 
                                          jwt_provider_config, test_jwt_token, 
                                          mock_oidc_config, rsa_key_pair):
        """Test successful token validation."""
        token, payload = test_jwt_token
        private_key, public_key, _, _ = rsa_key_pair
        
        # Mock OIDC discovery
        mock_response = Mock()
        mock_response.json.return_value = mock_oidc_config
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Mock JWKS client
        mock_signing_key = Mock()
        mock_signing_key.key = public_key
        mock_jwks_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
        
        validator = JWTValidator(jwt_provider_config)
        context = await validator.validate_token(token)
        
        assert context.subject == "test-user"
        assert context.email == "test@example.com"
        assert "users" in context.groups
        assert "user" in context.roles


# Test Azure EntraID Validator
class TestAzureEntraIDValidator:
    """Test Azure EntraID specific validation."""
    
    @pytest.fixture
    def azure_provider_config(self):
        """Azure EntraID provider configuration."""
        return JWTProviderConfig(
            name="azure-entraid",
            type="azure-entraid",
            issuer="https://login.microsoftonline.com/test-tenant/v2.0",
            tenant_id="test-tenant",
            audience="test-audience",
            algorithms=["RS256"]
        )
    
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_azure_oidc_discovery(self, mock_client, azure_provider_config):
        """Test Azure-specific OIDC discovery."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "issuer": "https://login.microsoftonline.com/test-tenant/v2.0",
            "jwks_uri": "https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys"
        }
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        validator = AzureEntraIDValidator(azure_provider_config)
        await validator._discover_oidc_config()
        
        assert validator._oidc_config["issuer"] == azure_provider_config.issuer


# Test AWS IAM Validator
class TestAWSIAMValidator:
    """Test AWS IAM specific validation."""
    
    @pytest.fixture
    def aws_provider_config(self):
        """AWS IAM provider configuration."""
        return JWTProviderConfig(
            name="aws-iam",
            type="aws-iam",
            issuer="https://oidc.eks.us-east-1.amazonaws.com/id/test-cluster",
            region="us-east-1",
            audience="sts.amazonaws.com",
            algorithms=["RS256"]
        )
    
    def test_aws_validator_initialization(self, aws_provider_config):
        """Test AWS IAM validator initialization."""
        validator = AWSIAMValidator(aws_provider_config)
        assert validator.config.region == "us-east-1"
        assert validator.config.type == "aws-iam"


# Test Validator Factory
class TestJWTValidatorFactory:
    """Test JWT validator factory."""
    
    def test_create_oidc_validator(self, jwt_provider_config):
        """Test creating OIDC validator."""
        validator = JWTValidatorFactory.create_validator(jwt_provider_config)
        assert isinstance(validator, JWTValidator)
    
    def test_create_azure_validator(self):
        """Test creating Azure EntraID validator."""
        config = JWTProviderConfig(
            name="azure",
            type="azure-entraid",
            issuer="https://login.microsoftonline.com/tenant/v2.0",
            audience="test"
        )
        validator = JWTValidatorFactory.create_validator(config)
        assert isinstance(validator, AzureEntraIDValidator)
    
    def test_create_aws_validator(self):
        """Test creating AWS IAM validator."""
        config = JWTProviderConfig(
            name="aws",
            type="aws-iam",
            issuer="https://oidc.eks.us-east-1.amazonaws.com/id/cluster",
            audience="sts.amazonaws.com"
        )
        validator = JWTValidatorFactory.create_validator(config)
        assert isinstance(validator, AWSIAMValidator)


# Test Domain Authenticator
class TestDomainAuthenticator:
    """Test domain-specific authentication."""
    
    @pytest.mark.asyncio
    async def test_authorization_success(self, domain_auth_config, jwt_provider_config):
        """Test successful authorization."""
        mock_validator = AsyncMock()
        context = SecurityContext(
            subject="test-user",
            groups=["users"],
            roles=["viewer"],
            claims={}
        )
        mock_validator.validate_token.return_value = context
        
        authenticator = DomainAuthenticator(domain_auth_config, mock_validator)
        result = await authenticator.authenticate_request("test-token")
        
        assert result == context
    
    @pytest.mark.asyncio
    async def test_authorization_failure_groups(self, domain_auth_config, jwt_provider_config):
        """Test authorization failure due to missing groups."""
        mock_validator = AsyncMock()
        context = SecurityContext(
            subject="test-user",
            groups=["other-group"],  # Missing required 'users' group
            roles=["viewer"],
            claims={}
        )
        mock_validator.validate_token.return_value = context
        
        authenticator = DomainAuthenticator(domain_auth_config, mock_validator)
        
        with pytest.raises(JWTValidationError, match="insufficient permissions"):
            await authenticator.authenticate_request("test-token")


# Test Authentication Manager
class TestAuthenticationManager:
    """Test authentication manager."""
    
    def test_authentication_enabled_check(self, auth_config):
        """Test checking if authentication is enabled for domain."""
        manager = AuthenticationManager(auth_config)
        
        assert manager.is_authentication_enabled("TEST_DOMAIN")
        assert not manager.is_authentication_enabled("UNKNOWN_DOMAIN")
    
    def test_get_domain_authenticator(self, auth_config):
        """Test getting domain authenticator."""
        manager = AuthenticationManager(auth_config)
        
        authenticator = manager.get_domain_authenticator("TEST_DOMAIN")
        assert authenticator is not None
        assert isinstance(authenticator, DomainAuthenticator)
        
        # Test caching
        authenticator2 = manager.get_domain_authenticator("TEST_DOMAIN")
        assert authenticator is authenticator2


# Integration Tests
class TestJWTAuthenticationIntegration:
    """Integration tests for JWT authentication system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_authentication(self, auth_config, test_jwt_token, rsa_key_pair):
        """Test end-to-end authentication flow."""
        token, payload = test_jwt_token
        
        # This would require more complex mocking for a full integration test
        # but demonstrates the flow
        manager = AuthenticationManager(auth_config)
        authenticator = manager.get_domain_authenticator("TEST_DOMAIN")
        
        assert authenticator is not None
        assert manager.is_authentication_enabled("TEST_DOMAIN")
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Test invalid provider type
        with pytest.raises(ValueError):
            JWTProviderConfig(
                name="invalid",
                type="invalid-type",
                issuer="https://example.com",
                audience="test"
            )
        
        # Test missing provider for enabled domain
        with pytest.raises(ValueError):
            DomainAuthConfig(
                enabled=True,
                required=True,
                provider=None  # Should fail validation
            )


if __name__ == "__main__":
    pytest.main([__file__])