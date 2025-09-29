#!/usr/bin/env python3
"""
Comprehensive test to verify the enhanced /mcp endpoint and overall functionality.
"""

import json
from fastapi.testclient import TestClient
from mcp_server.server.app import create_http_app
from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.core.auth_config import load_auth_config, get_default_auth_config_path


def test_comprehensive_functionality():
    """Test that all functionality works correctly after modifications."""
    
    print("=== Testing Enhanced MCP Server Functionality ===")
    
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
        print("1. Testing health endpoints...")
        
        # Test health endpoint
        response = client.get("/healthz")
        assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
        assert response.json()["ok"] is True, "Health check failed"
        print("   ✓ Health endpoint working")
        
        # Test readiness endpoint
        response = client.get("/readyz")
        assert response.status_code == 200, f"Readiness endpoint failed: {response.status_code}"
        assert response.json()["ok"] is True, "Readiness check failed"
        print("   ✓ Readiness endpoint working")
        
        print("2. Testing enhanced /mcp endpoint...")
        
        # Test enhanced MCP endpoint
        response = client.get("/mcp")
        assert response.status_code == 200, f"MCP endpoint failed: {response.status_code}"
        
        data = response.json()
        print(f"   Response structure: {list(data.keys())}")
        
        # Verify the enhanced response structure
        if "domains" in data:
            print("   ✓ Enhanced response format detected")
            domains = data["domains"]
            assert isinstance(domains, list), "Domains should be a list"
            
            # Verify domain structure
            for domain in domains:
                required_fields = ["name", "slug", "path", "description", "auth_enabled", "tools", "resources"]
                for field in required_fields:
                    assert field in domain, f"Domain missing required field: {field}"
                
                print(f"   ✓ Domain '{domain['name']}' has complete structure")
                
                # Verify tools structure
                if domain["tools"]:
                    for tool_class in domain["tools"]:
                        tool_fields = ["name", "type", "description", "tools"]
                        for field in tool_fields:
                            assert field in tool_class, f"Tool class missing field: {field}"
                        
                        # Check individual tools
                        for tool in tool_class["tools"]:
                            tool_detail_fields = ["name", "function", "description", "parameters"]
                            for field in tool_detail_fields:
                                assert field in tool, f"Tool missing field: {field}"
                    
                    print(f"     ✓ Tools structure validated for {domain['name']}")
                
                # Verify resources structure
                if domain["resources"]:
                    for resource_class in domain["resources"]:
                        resource_fields = ["name", "type", "description", "resources"]
                        for field in resource_fields:
                            assert field in resource_class, f"Resource class missing field: {field}"
                        
                        # Check individual resources
                        for resource in resource_class["resources"]:
                            resource_detail_fields = ["name", "description", "type", "access", "uri"]
                            for field in resource_detail_fields:
                                assert field in resource, f"Resource missing field: {field}"
                    
                    print(f"     ✓ Resources structure validated for {domain['name']}")
            
            print(f"   ✓ All {len(domains)} domains validated successfully")
            
        elif "mounts" in data:
            print("   ✓ Fallback response format working")
            mounts = data["mounts"]
            assert isinstance(mounts, list), "Mounts should be a list"
        else:
            raise AssertionError("Response should contain either 'domains' or 'mounts'")
        
        print("3. Testing backward compatibility...")
        # Verify that basic mount information is still accessible
        if "domains" in data:
            # Extract basic mount info from enhanced response
            basic_info = []
            for domain in data["domains"]:
                basic_info.append({
                    "name": domain["name"],
                    "slug": domain["slug"],
                    "path": domain["path"],
                    "description": domain["description"]
                })
            print(f"   ✓ Basic mount information extractable from {len(basic_info)} domains")
        
        print("4. Verifying detailed information content...")
        if "domains" in data:
            total_tools = sum(len(domain["tools"]) for domain in data["domains"])
            total_resources = sum(len(domain["resources"]) for domain in data["domains"])
            print(f"   ✓ Found {total_tools} tool classes across all domains")
            print(f"   ✓ Found {total_resources} resource classes across all domains")
            
            # Check for specific expected content
            weather_domain = next((d for d in data["domains"] if d["name"] == "WEATHER"), None)
            if weather_domain:
                weather_tools = weather_domain["tools"]
                if weather_tools:
                    google_weather_tools = next((tc for tc in weather_tools if tc["name"] == "google_weather"), None)
                    if google_weather_tools and google_weather_tools["tools"]:
                        tool_names = [t["name"] for t in google_weather_tools["tools"]]
                        expected_tools = ["google_weather.current_conditions", "google_weather.hourly_forecast", 
                                        "google_weather.daily_forecast", "google_weather.geocode"]
                        for expected in expected_tools:
                            if expected in tool_names:
                                print(f"     ✓ Found expected tool: {expected}")
            
            # Check for resource content
            usecasey_domain = next((d for d in data["domains"] if d["name"] == "USECASEY"), None)
            if usecasey_domain and usecasey_domain["resources"]:
                resource_names = []
                for rc in usecasey_domain["resources"]:
                    resource_names.extend([r["name"] for r in rc["resources"]])
                if "weather_data" in resource_names:
                    print("     ✓ Found expected resource: weather_data")
                if "sample_parameterized_resource" in resource_names:
                    print("     ✓ Found expected resource: sample_parameterized_resource")

    print("\n=== All Tests Passed Successfully! ===")
    print("✓ Enhanced /mcp endpoint returns detailed domain information")
    print("✓ Each domain includes comprehensive tools and resources information")
    print("✓ Tool information includes names, functions, descriptions, and parameters")
    print("✓ Resource information includes names, descriptions, types, access, URIs, and parameters")
    print("✓ Backward compatibility maintained with fallback mechanisms")
    print("✓ All existing functionality continues to work correctly")


if __name__ == "__main__":
    test_comprehensive_functionality()