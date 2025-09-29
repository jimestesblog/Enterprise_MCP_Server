#!/usr/bin/env python3
"""
Test script to check the current behavior of the /mcp endpoint
and verify our modifications work correctly.
"""

import asyncio
import httpx
from mcp_server.server.app import create_http_app
from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.core.auth_config import load_auth_config, get_default_auth_config_path


async def test_mcp_endpoint():
    """Test the /mcp endpoint before and after modifications."""
    
    # Load configuration
    config_path = get_default_config_path()
    config = load_config(config_path) if config_path else None
    
    # Load authentication configuration
    auth_config_path = get_default_auth_config_path()
    auth_config = load_auth_config(auth_config_path) if auth_config_path else None
    
    # Create application
    app = create_http_app(config, auth_config)
    
    print("=== Current /mcp endpoint response ===")
    
    # Test the endpoint using a test client
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        response = client.get("/mcp")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    
    print("\n=== Configuration details ===")
    if config:
        print(f"Domains: {len(config.Domains) if config.Domains else 0}")
        print(f"MCP Classes: {len(config.mcp_classes) if config.mcp_classes else 0}")
        
        if config.Domains:
            for domain in config.Domains:
                print(f"  Domain: {domain}")
                
        if config.mcp_classes:
            for mcp_class in config.mcp_classes[:2]:  # Show first 2 for brevity
                print(f"  MCP Class: {mcp_class.get('class_name', 'N/A')} in domain {mcp_class.get('Domain', 'N/A')}")
                print(f"    Tools: {len(mcp_class.get('tools', []))}")
                print(f"    Resources: {len(mcp_class.get('resources', []))}")


if __name__ == "__main__":
    asyncio.run(test_mcp_endpoint())