#!/usr/bin/env python3
"""
Test script to verify MCP resource exposure via FastMCP protocol.

This script tests that resources defined in tools.yaml are properly
exposed through the MCP protocol endpoints and can be accessed via
the standard MCP resource methods.
"""

import asyncio
import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.server.factory import ServerFactory
from mcp.server.fastmcp import FastMCP


async def test_mcp_resource_listing():
    """Test that resources are properly listed via MCP protocol."""
    print("=== Testing MCP Resource Listing ===")
    
    try:
        # Create a standalone FastMCP app for testing
        usecasey_app = FastMCP(name="USECASEY")
        print(f"✓ USECASEY FastMCP app created: {type(usecasey_app)}")
        
        # Test initial state - should have no resources
        resources = await usecasey_app.list_resources()
        print(f"📋 Initial resources count: {len(resources)}")
        
        # Create and register resource instances directly using current method
        # This simulates what the factory does
        from mcp_server.resources.example1.publichttpresource import HttpResource
        from mcp_server.resources.example1.privateresourceexample import ExamplePrivateResources
        
        # Create HTTP resource instance
        http_config = {
            "name": "http_resources",
            "params": {
                "resources": [
                    {
                        "name": "weather_data",
                        "description": "static weather data.",
                        "type": "csv",
                        "access": "public",
                        "uri": "https://raw.githubusercontent.com/velicki/Weather_Data_Analysis_Project/refs/heads/main/Weather_Data.csv"
                    }
                ]
            }
        }
        http_resource = HttpResource(http_config)
        
        # Test current registration method (should fail to expose via MCP)
        print("🔍 Testing current registration method (setattr)...")
        setattr(usecasey_app, "_resource_weather_data", lambda params=None: http_resource.get_resource_content("weather_data", params))
        
        # Check if resources are now listed
        resources = await usecasey_app.list_resources()
        print(f"📋 Resources after current method: {len(resources)}")
        
        if len(resources) == 0:
            print("❌ Current method doesn't expose resources via MCP protocol - confirming the issue!")
            return False
        else:
            print("✓ Resources found via MCP protocol with current method")
            return True
            
    except Exception as e:
        print(f"❌ Error in resource listing test: {e}")
        traceback.print_exc()
        return False


async def test_mcp_resource_reading():
    """Test that resources can be read via MCP protocol."""
    print("\n=== Testing MCP Resource Reading ===")
    
    try:
        # Create a standalone FastMCP app for testing
        usecasey_app = FastMCP(name="USECASEY")
        
        # Test trying to read a non-existent resource
        test_uris = [
            "weather_data",
            "sample_parameterized_resource"
        ]
        
        for uri in test_uris:
            try:
                print(f"🔍 Attempting to read resource: {uri}")
                content = await usecasey_app.read_resource(uri)
                print(f"✓ Successfully read resource {uri}")
                # Convert async generator to list to check content
                content_list = [item async for item in content]
                print(f"  Content blocks: {len(content_list)}")
                return True
            except Exception as e:
                print(f"❌ Failed to read resource {uri}: {e}")
        
        print("❌ No resources could be read - confirming resources aren't exposed")
        return False
        
    except Exception as e:
        print(f"❌ Error in resource reading test: {e}")
        traceback.print_exc()
        return False


async def test_current_resource_registration():
    """Test the current resource registration mechanism to understand what's happening."""
    print("=== Testing Current Resource Registration ===")
    
    try:
        # Create standalone FastMCP app
        usecasey_app = FastMCP(name="USECASEY")
        
        print("🔍 FastMCP app before resource registration:")
        initial_resources = await usecasey_app.list_resources()
        print(f"  Initial resources: {len(initial_resources)}")
        
        # Simulate current broken registration method
        from mcp_server.resources.example1.publichttpresource import HttpResource
        
        http_config = {
            "name": "http_resources",
            "params": {
                "resources": [
                    {
                        "name": "weather_data",
                        "description": "static weather data.",
                        "type": "csv",
                        "access": "public",
                        "uri": "https://example.com/weather.csv"
                    }
                ]
            }
        }
        http_resource = HttpResource(http_config)
        
        # Add custom attribute (current broken method)
        setattr(usecasey_app, "_resource_weather_data", lambda params=None: "mock content")
        
        print("\n🔍 FastMCP app after resource registration:")
        resource_attrs = [attr for attr in dir(usecasey_app) if attr.startswith('_resource_')]
        print(f"  Custom resource attributes: {resource_attrs}")
        
        # Check resources via MCP protocol
        resources_after = await usecasey_app.list_resources()
        print(f"  MCP protocol resources: {len(resources_after)}")
        
        # Check if custom attributes were added (current broken implementation)
        if resource_attrs and len(resources_after) == 0:
            print("✓ Confirmed: Custom attributes added but NOT exposed via MCP protocol")
            return True
        else:
            print("❌ Unexpected state")
            return False
            
    except Exception as e:
        print(f"❌ Error testing current registration: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all MCP resource exposure tests."""
    print("=== MCP Server Resource Exposure Test ===\n")
    
    results = []
    
    # Test current registration mechanism
    results.append(await test_current_resource_registration())
    
    # Test MCP resource listing
    results.append(await test_mcp_resource_listing())
    
    # Test MCP resource reading
    results.append(await test_mcp_resource_reading())
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if results[0] and not results[1]:
        print("🔍 Analysis: Resources are being registered as custom attributes but NOT via MCP protocol")
        print("💡 Solution: Need to use FastMCP.add_resource() instead of setattr()")
        return 0
    elif all(results):
        print("✅ All tests passed - resources are properly exposed via MCP protocol")
        return 0
    else:
        print("❌ Unexpected test pattern - needs investigation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)