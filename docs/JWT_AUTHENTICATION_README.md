# JWT Authentication for MCP Server

This document describes the JWT token authentication system implemented for the MCP Server, providing per-domain authentication with support for Azure EntraID, AWS IAM, and OIDC-compliant identity providers.

## Overview

The JWT authentication system allows you to:
- Configure JWT token validation individually for each domain/mount point
- Support multiple identity providers (Azure EntraID, AWS IAM, OIDC)
- Enable/disable authentication per domain
- Extract user claims and build security contexts
- Implement role-based and group-based authorization

## Architecture

The authentication system consists of:

1. **Configuration System** (`mcp_server/core/auth_config.py`)
   - `JWTProviderConfig`: Defines identity provider settings
   - `DomainAuthConfig`: Per-domain authentication configuration
   - `AuthConfig`: Main configuration container

2. **Token Validation** (`mcp_server/core/auth_validator.py`)
   - `JWTValidator`: Base OIDC-compliant token validator
   - `AzureEntraIDValidator`: Azure-specific token validator
   - `AWSIAMValidator`: AWS IAM-specific token validator
   - `SecurityContext`: Extracted user identity and claims

3. **Middleware Integration** (`mcp_server/core/auth_middleware.py`)
   - `JWTAuthenticationMiddleware`: FastAPI middleware for token validation
   - `AuthenticationManager`: Manages domain-specific authenticators
   - FastAPI dependencies for security context access

4. **Server Integration** (`mcp_server/server/factory.py`, `mcp_server/server/app.py`)
   - Integrated with existing ServerFactory and domain mounting
   - Automatic middleware application based on configuration

## Configuration

### auth.yaml Structure

Create `config/auth.yaml` with the following structure:

```yaml
# Global settings
default_enabled: false

# Identity providers
providers:
  azure-entraid:
    name: azure-entraid
    type: azure-entraid
    issuer: "https://login.microsoftonline.com/${AZURE_TENANT_ID}/v2.0"
    tenant_id: "${AZURE_TENANT_ID}"
    audience: "${AZURE_CLIENT_ID}"
    algorithms: ["RS256"]

  aws-iam:
    name: aws-iam
    type: aws-iam
    issuer: "https://oidc.eks.${AWS_REGION}.amazonaws.com/id/${EKS_CLUSTER_ID}"
    region: "${AWS_REGION}"
    audience: "sts.amazonaws.com"

  generic-oidc:
    name: generic-oidc
    type: oidc
    issuer: "${OIDC_ISSUER_URL}"
    audience: "${OIDC_AUDIENCE}"

# Per-domain authentication
domains:
  WEATHER:
    enabled: true
    required: true
    provider: azure-entraid
    require_groups: ["weather-users"]
    
  USECASEX:
    enabled: true
    required: true
    provider: aws-iam
    require_roles: ["ReadOnlyAccess"]
```

### Environment Variables

Set the following environment variables:

```bash
# Azure EntraID
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_CLIENT_ID=your-azure-client-id

# AWS IAM
AWS_REGION=us-east-1
EKS_CLUSTER_ID=your-eks-cluster-id

# Generic OIDC
OIDC_ISSUER_URL=https://your-oidc-provider.com
OIDC_AUDIENCE=your-audience

# Optional: Custom auth config path
AUTH_CONFIG_PATH=/path/to/auth.yaml
```

## Provider Types

### Azure EntraID (`azure-entraid`)
- Automatically discovers Azure v2.0 endpoints
- Supports tenant-specific configuration
- Handles Azure-specific group and role claims

### AWS IAM (`aws-iam`)
- Supports EKS OIDC providers
- Handles AWS-specific role claims
- Regional configuration support

### Generic OIDC (`oidc`)
- Standard OIDC Discovery protocol
- Compatible with Auth0, Keycloak, etc.
- Customizable claims mapping

## Domain Configuration

For each domain in `tools.yaml`, you can configure authentication in `auth.yaml`:

```yaml
domains:
  DOMAIN_NAME:
    enabled: true          # Enable authentication for this domain
    required: true         # Require authentication (vs optional)
    provider: provider-name # Which provider to use
    require_groups: []     # Required user groups
    require_roles: []      # Required user roles
    required_claims: {}    # Additional required claims
```

## Usage

### Authentication Flow

1. Client includes JWT token in `Authorization: Bearer <token>` header
2. Middleware validates token against configured provider
3. Security context is extracted and attached to request
4. Authorization rules are checked (groups, roles, claims)
5. Request proceeds if authentication/authorization succeeds

### Accessing Security Context

In FastAPI endpoints, use dependencies to access security context:

```python
from fastapi import Depends, Request
from mcp_server.core.auth_middleware import get_security_context, require_authentication

# Optional authentication
async def my_endpoint(request: Request):
    context = get_security_context(request)
    if context:
        user_id = context.subject
        user_groups = context.groups

# Required authentication
async def protected_endpoint(context: SecurityContext = Depends(require_authentication)):
    user_id = context.subject
    user_email = context.email
    user_groups = context.groups
```

### Group/Role Requirements

Use dependency factories for specific authorization requirements:

```python
from mcp_server.core.auth_middleware import require_groups, require_roles

# Require specific groups
async def admin_endpoint(context: SecurityContext = Depends(require_groups("admins", "super-users"))):
    # User has one of the required groups
    pass

# Require specific roles
async def editor_endpoint(context: SecurityContext = Depends(require_roles("editor", "admin"))):
    # User has one of the required roles
    pass
```

## Testing

### Running Tests

```bash
# Install dependencies
pip install PyJWT>=2.8.0 cryptography>=41.0.0

# Run smoke tests
python test_auth_smoke.py

# Run full test suite
python -m pytest tests/test_jwt_auth.py -v
```

### Test Results

The smoke test validates:
- ✅ Authentication component imports
- ✅ Configuration creation and validation
- ✅ JWT validator factory (OIDC, Azure, AWS)
- ✅ Authentication manager functionality
- ✅ Security context operations
- ✅ Configuration loading from auth.yaml

## Security Considerations

1. **Token Validation**: All tokens are validated using OIDC Discovery and JWKS
2. **Signature Verification**: RSA/ECDSA signatures are cryptographically verified
3. **Time-based Claims**: Expiration and issued-at times are validated
4. **Audience Verification**: Tokens must be issued for the correct audience
5. **Issuer Verification**: Tokens must come from trusted issuers
6. **HTTPS Required**: Use HTTPS in production to protect tokens in transit

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PyJWT and cryptography are installed
2. **Configuration Errors**: Validate auth.yaml syntax and provider configuration
3. **Token Validation Failures**: Check issuer URLs, audience, and algorithm settings
4. **OIDC Discovery Failures**: Verify issuer URLs are accessible and correct

### Debug Logging

Enable debug logging to troubleshoot authentication issues:

```python
import logging
logging.getLogger('mcp_server.core.auth_validator').setLevel(logging.DEBUG)
logging.getLogger('mcp_server.core.auth_middleware').setLevel(logging.DEBUG)
```

### Testing Tokens

Use online JWT decoders to inspect token contents and verify claims match your configuration.

## Migration from Existing Setup

1. Create `config/auth.yaml` with your provider configurations
2. Add domain authentication settings for existing domains
3. Set required environment variables
4. Restart the MCP server
5. Test authentication with valid JWT tokens

The system is backward compatible - domains without authentication configuration will continue to work without authentication.

## API Endpoints

### Authentication Status

Check authentication status for mounted domains:

```bash
GET /mcp
```

Response includes `auth_enabled` flag for each domain:

```json
{
  "mounts": [
    {
      "name": "WEATHER",
      "slug": "weather",
      "path": "/mcp/weather",
      "description": "Weather tools",
      "auth_enabled": true
    }
  ]
}
```

## Support

For issues or questions regarding JWT authentication:

1. Check this documentation
2. Run the smoke test to validate your setup
3. Review server logs for authentication errors
4. Verify your auth.yaml configuration
5. Test with known-good JWT tokens