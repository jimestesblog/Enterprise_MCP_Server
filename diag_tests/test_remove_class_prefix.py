#!/usr/bin/env python3
"""
Test script to verify that the /mcp endpoint no longer contains 
"class_" prefixes in JSON property names.
"""

import json
from fastapi.testclient import TestClient
from mcp_server.server.app import create_http_app
from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.core.auth_config import load_auth_config, get_default_auth_config_path


def check_for_class_prefix(obj, path=""):
    """Recursively check for any JSON keys with 'class_' prefix."""
    class_prefix_keys = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if this key has class_ prefix
            if key.startswith("class_"):
                class_prefix_keys.append(current_path)
            
            # Recursively check nested objects
            nested_keys = check_for_class_prefix(value, current_path)
            class_prefix_keys.extend(nested_keys)
            
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            nested_keys = check_for_class_prefix(item, current_path)
            class_prefix_keys.extend(nested_keys)
    
    return class_prefix_keys


def test_remove_class_prefix():
    """Test that no 'class_' prefixes remain in the /mcp endpoint response."""
    
    print("=== Testing Removal of 'class_' Prefixes from /mcp Endpoint ===")
    
    # Load configuration
    config_path = get_default_config_path()
    config = load_config(config_path) if config_path else None
    
    # Load authentication configuration
    auth_config_path = get_default_auth_config_path()
    auth_config = load_auth_config(auth_config_path) if auth_config_path else None
    
    # Create application
    app = create_http_app(config, auth_config)
    
    # Test the application with a test client
    with TestClient(app) as client:
        print("1. Testing /mcp endpoint response...")
        
        # Get the MCP endpoint response
        response = client.get("/mcp")
        assert response.status_code == 200, f"MCP endpoint failed: {response.status_code}"
        
        data = response.json()
        print(f"   Response structure: {list(data.keys())}")
        
        # Check for any remaining class_ prefixes
        class_prefix_keys = check_for_class_prefix(data)
        
        if class_prefix_keys:
            print(f"   ❌ Found {len(class_prefix_keys)} properties with 'class_' prefix:")
            for key_path in class_prefix_keys:
                print(f"     - {key_path}")
            raise AssertionError("Found JSON properties with 'class_' prefix")
        else:
            print("   ✓ No 'class_' prefixes found in response")
        
        print("2. Verifying expected property names are present...")
        
        if "domains" in data:
            domains = data["domains"]
            tool_classes_found = 0
            resource_classes_found = 0
            
            for domain in domains:
                # Check tools structure
                if domain.get("tools"):
                    for tool_class in domain["tools"]:
                        tool_classes_found += 1
                        
                        # Verify new property names exist
                        required_props = ["name", "type", "description", "tools"]
                        for prop in required_props:
                            assert prop in tool_class, f"Tool class missing property: {prop}"
                        
                        print(f"     ✓ Tool class '{tool_class['name']}' has correct properties")
                
                # Check resources structure
                if domain.get("resources"):
                    for resource_class in domain["resources"]:
                        resource_classes_found += 1
                        
                        # Verify new property names exist
                        required_props = ["name", "type", "description", "resources"]
                        for prop in required_props:
                            assert prop in resource_class, f"Resource class missing property: {prop}"
                        
                        print(f"     ✓ Resource class '{resource_class['name']}' has correct properties")
            
            print(f"   ✓ Verified {tool_classes_found} tool classes and {resource_classes_found} resource classes")
        
        print("3. Testing functionality still works...")
        
        # Test health endpoints to ensure nothing is broken
        health_response = client.get("/healthz")
        assert health_response.status_code == 200, "Health endpoint broken"
        assert health_response.json()["ok"] is True, "Health check failed"
        print("   ✓ Health endpoint still working")
        
        readiness_response = client.get("/readyz")
        assert readiness_response.status_code == 200, "Readiness endpoint broken"
        assert readiness_response.json()["ok"] is True, "Readiness check failed"
        print("   ✓ Readiness endpoint still working")
        
        print("4. Showing sample of updated response format...")
        
        if "domains" in data and data["domains"]:
            sample_domain = data["domains"][0]
            print(f"   Sample domain: {sample_domain['name']}")
            
            if sample_domain.get("tools"):
                sample_tool_class = sample_domain["tools"][0]
                print(f"   Sample tool class properties:")
                print(f"     - name: {sample_tool_class.get('name')}")
                print(f"     - type: {sample_tool_class.get('type')}")
                print(f"     - description: {sample_tool_class.get('description')}")
            
            if sample_domain.get("resources"):
                sample_resource_class = sample_domain["resources"][0]
                print(f"   Sample resource class properties:")
                print(f"     - name: {sample_resource_class.get('name')}")
                print(f"     - type: {sample_resource_class.get('type')}")
                print(f"     - description: {sample_resource_class.get('description')}")

    print("\n=== All Tests Passed Successfully! ===")
    print("✓ No 'class_' prefixes found in /mcp endpoint response")
    print("✓ All JSON properties now use clean names without 'class_' prefix")
    print("✓ Tool classes use: 'name', 'type', 'description' instead of 'class_name', 'class_type', 'class_description'")
    print("✓ Resource classes use: 'name', 'type', 'description' instead of 'class_name', 'class_type', 'class_description'")
    print("✓ All existing functionality continues to work correctly")


if __name__ == "__main__":
    test_remove_class_prefix()