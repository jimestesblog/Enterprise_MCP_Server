#!/usr/bin/env python3
"""
Smoke test for JWT authentication implementation.

This script validates that the authentication system components
can be imported and initialized correctly.
"""

import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all authentication components can be imported."""
    print("Testing authentication component imports...")
    
    try:
        # Test core authentication imports
        from mcp_server.core.auth_config import (
            JWTProviderConfig, DomainAuthConfig, AuthConfig,
            load_auth_config, get_default_auth_config_path
        )
        print("✓ Authentication configuration imports successful")
        
        from mcp_server.core.auth_validator import (
            JWTValidator, AzureEntraIDValidator, AWSIAMValidator,
            JWTValidatorFactory, DomainAuthenticator, SecurityContext,
            JWTValidationError
        )
        print("✓ Authentication validator imports successful")
        
        from mcp_server.core.auth_middleware import (
            JWTAuthenticationMiddleware, AuthenticationManager,
            get_security_context, require_authentication
        )
        print("✓ Authentication middleware imports successful")
        
        # Test dependency imports
        import jwt
        import httpx
        from cryptography.hazmat.primitives import serialization
        print("✓ Required dependency imports successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False


def test_configuration_creation():
    """Test creating authentication configuration objects."""
    print("\nTesting authentication configuration creation...")
    
    try:
        # Create a test JWT provider configuration
        provider_config = JWTProviderConfig(
            name="test-provider",
            type="oidc",
            issuer="https://test-issuer.com",
            audience="test-audience",
            algorithms=["RS256"]
        )
        print(f"✓ Created JWT provider config: {provider_config.name}")
        
        # Create a test domain authentication configuration
        domain_config = DomainAuthConfig(
            enabled=True,
            required=True,
            provider="test-provider",
            require_groups=["users"],
            require_roles=["viewer"]
        )
        print(f"✓ Created domain auth config: enabled={domain_config.enabled}")
        
        # Create main authentication configuration
        auth_config = AuthConfig(
            default_enabled=False,
            providers={"test-provider": provider_config},
            domains={"TEST_DOMAIN": domain_config}
        )
        print(f"✓ Created main auth config with {len(auth_config.providers)} providers")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration creation failed: {e}")
        traceback.print_exc()
        return False


def test_validator_factory():
    """Test JWT validator factory functionality."""
    print("\nTesting JWT validator factory...")
    
    try:
        from mcp_server.core.auth_config import JWTProviderConfig
        from mcp_server.core.auth_validator import (
            JWTValidatorFactory, JWTValidator, AzureEntraIDValidator, AWSIAMValidator
        )
        
        # Test OIDC validator creation
        oidc_config = JWTProviderConfig(
            name="oidc-test",
            type="oidc",
            issuer="https://oidc-issuer.com",
            audience="test-audience"
        )
        oidc_validator = JWTValidatorFactory.create_validator(oidc_config)
        assert isinstance(oidc_validator, JWTValidator)
        print("✓ OIDC validator created successfully")
        
        # Test Azure validator creation
        azure_config = JWTProviderConfig(
            name="azure-test",
            type="azure-entraid",
            issuer="https://login.microsoftonline.com/tenant/v2.0",
            audience="azure-audience"
        )
        azure_validator = JWTValidatorFactory.create_validator(azure_config)
        assert isinstance(azure_validator, AzureEntraIDValidator)
        print("✓ Azure EntraID validator created successfully")
        
        # Test AWS validator creation
        aws_config = JWTProviderConfig(
            name="aws-test",
            type="aws-iam",
            issuer="https://oidc.eks.us-east-1.amazonaws.com/id/cluster",
            audience="sts.amazonaws.com"
        )
        aws_validator = JWTValidatorFactory.create_validator(aws_config)
        assert isinstance(aws_validator, AWSIAMValidator)
        print("✓ AWS IAM validator created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Validator factory test failed: {e}")
        traceback.print_exc()
        return False


def test_authentication_manager():
    """Test authentication manager functionality."""
    print("\nTesting authentication manager...")
    
    try:
        from mcp_server.core.auth_config import JWTProviderConfig, DomainAuthConfig, AuthConfig
        from mcp_server.core.auth_middleware import AuthenticationManager
        
        # Create test configuration
        provider_config = JWTProviderConfig(
            name="test-provider",
            type="oidc",
            issuer="https://test-issuer.com",
            audience="test-audience"
        )
        
        domain_config = DomainAuthConfig(
            enabled=True,
            required=True,
            provider="test-provider"
        )
        
        auth_config = AuthConfig(
            providers={"test-provider": provider_config},
            domains={"TEST_DOMAIN": domain_config}
        )
        
        # Test authentication manager
        auth_manager = AuthenticationManager(auth_config)
        
        # Test domain authentication check
        is_enabled = auth_manager.is_authentication_enabled("TEST_DOMAIN")
        assert is_enabled == True
        print("✓ Domain authentication check works")
        
        is_disabled = auth_manager.is_authentication_enabled("UNKNOWN_DOMAIN")
        assert is_disabled == False
        print("✓ Unknown domain authentication check works")
        
        return True
        
    except Exception as e:
        print(f"✗ Authentication manager test failed: {e}")
        traceback.print_exc()
        return False


def test_security_context():
    """Test security context functionality."""
    print("\nTesting security context...")
    
    try:
        from mcp_server.core.auth_validator import SecurityContext
        
        # Create test security context
        context = SecurityContext(
            subject="test-user",
            email="test@example.com",
            name="Test User",
            groups=["users", "admins"],
            roles=["viewer", "editor"],
            claims={"custom_claim": "custom_value"}
        )
        
        # Test group membership
        assert context.has_group("users") == True
        assert context.has_group("unknown") == False
        assert context.has_any_group(["unknown", "users"]) == True
        print("✓ Group membership checks work")
        
        # Test role membership
        assert context.has_role("viewer") == True
        assert context.has_role("unknown") == False
        assert context.has_any_role(["unknown", "viewer"]) == True
        print("✓ Role membership checks work")
        
        return True
        
    except Exception as e:
        print(f"✗ Security context test failed: {e}")
        traceback.print_exc()
        return False


def test_auth_config_loading():
    """Test authentication configuration loading from file."""
    print("\nTesting authentication configuration loading...")
    
    try:
        from mcp_server.core.auth_config import load_auth_config, get_default_auth_config_path
        
        # Test getting default auth config path
        auth_path = get_default_auth_config_path()
        if auth_path:
            print(f"✓ Found auth config path: {auth_path}")
            
            # Test loading auth configuration
            auth_config = load_auth_config(auth_path)
            print(f"✓ Loaded auth config with {len(auth_config.providers)} providers")
            print(f"✓ Loaded auth config with {len(auth_config.domains)} domain configs")
            
            # Validate some providers exist
            if auth_config.providers:
                for name, provider in auth_config.providers.items():
                    print(f"  - Provider: {name} (type: {provider.type})")
            
            # Validate some domains exist
            if auth_config.domains:
                for name, domain in auth_config.domains.items():
                    print(f"  - Domain: {name} (enabled: {domain.enabled})")
        else:
            print("! No auth config file found (this is expected if not created yet)")
            
            # Test loading empty config
            empty_config = load_auth_config(None)
            assert len(empty_config.providers) == 0
            assert len(empty_config.domains) == 0
            print("✓ Empty auth config loading works")
        
        return True
        
    except Exception as e:
        print(f"✗ Auth config loading test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all smoke tests."""
    print("JWT Authentication System Smoke Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration_creation,
        test_validator_factory,
        test_authentication_manager,
        test_security_context,
        test_auth_config_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"✗ Test {test.__name__} failed")
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Smoke Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All smoke tests passed! JWT authentication system is working.")
        return 0
    else:
        print("❌ Some smoke tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)