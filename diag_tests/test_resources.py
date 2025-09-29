#!/usr/bin/env python3
"""
Test script for MCP Server resources functionality.

This script tests both public HTTP resources and private MCP server resources
to ensure the resource system is working correctly.
"""

import asyncio
import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.resources.example1.publichttpresource import HttpResource
from mcp_server.resources.example1.privateresourceexample import ExamplePrivateResources


async def test_public_http_resource():
    """Test the public HTTP resource functionality."""
    print("Testing public HTTP resource...")
    
    # Create HttpResource instance with test configuration
    config = {
        "name": "http_resources",
        "description": "Test HTTP resources",
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
    
    try:
        resource = HttpResource(config)
        print(f"Created HttpResource with {len(resource.resource_instances)} resource(s)")
        
        # Test fetching the weather data
        content = await resource.get_resource_content("weather_data")
        print(f"Successfully fetched {len(content)} characters from weather_data")
        print(f"First 200 characters: {content[:200]}...")
        
        return True
    except Exception as e:
        print(f"Error testing public HTTP resource: {e}")
        traceback.print_exc()
        return False


async def test_private_mcp_resource():
    """Test the private MCP server resource functionality."""
    print("\nTesting private MCP server resource...")
    
    # Create ExamplePrivateResources instance with test configuration
    config = {
        "name": "example_private_resources",
        "description": "Test private resources",
        "params": {
            "resources": [
                {
                    "name": "sample_parameterized_resource",
                    "description": "sample parameterized resource.",
                    "function": "_sample_parameterized_resource",
                    "type": "txt",
                    "access": "mcp_server",
                    "uri": "//sampledata/{client}/",
                    "resource_parameters": [
                        {
                            "name": "client",
                            "description": "Client ID.",
                            "allowed_values": "string"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        resource = ExamplePrivateResources(config)
        print(f"Created ExamplePrivateResources with {len(resource.resource_instances)} resource(s)")
        
        # Test with 'acme' client
        content_acme = await resource.get_resource_content("sample_parameterized_resource", {"client": "acme"})
        print(f"ACME client response: {content_acme}")
        
        # Test with 'bigrock' client
        content_bigrock = await resource.get_resource_content("sample_parameterized_resource", {"client": "bigrock"})
        print(f"BigRock client response: {content_bigrock}")
        
        # Test with unknown client
        content_unknown = await resource.get_resource_content("sample_parameterized_resource", {"client": "unknown"})
        print(f"Unknown client response: {content_unknown}")
        
        # Verify expected responses
        expected_acme = "This is the roadrunner client"
        expected_bigrock = "We make tools to smash birds"
        
        if content_acme == expected_acme and content_bigrock == expected_bigrock:
            print("✓ Parameterized responses match expected values")
            return True
        else:
            print("✗ Parameterized responses don't match expected values")
            return False
            
    except Exception as e:
        print(f"Error testing private MCP resource: {e}")
        traceback.print_exc()
        return False


async def test_configuration_loading():
    """Test loading resources from configuration."""
    print("\nTesting configuration loading...")
    
    try:
        config_path = get_default_config_path()
        if not config_path:
            print("No configuration file found")
            return False
        
        config = load_config(config_path)
        print(f"Loaded configuration with {len(config.resources)} resource classes")
        
        for resource_config in config.resources:
            print(f"- {resource_config.name}: {resource_config.class_type}")
            print(f"  Resources: {[r.name for r in resource_config.resources]}")
        
        return len(config.resources) > 0
        
    except Exception as e:
        print(f"Error testing configuration loading: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all resource tests."""
    print("=== MCP Server Resources Test ===\n")
    
    results = []
    
    # Test public HTTP resource
    results.append(await test_public_http_resource())
    
    # Test private MCP resource
    results.append(await test_private_mcp_resource())
    
    # Test configuration loading
    results.append(await test_configuration_loading())
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)