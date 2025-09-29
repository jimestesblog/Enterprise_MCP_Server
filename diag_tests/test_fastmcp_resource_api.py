#!/usr/bin/env python3
"""
Test script to understand FastMCP Resource API requirements.

This script experiments with the FastMCP add_resource method to understand
what type of Resource object it expects.
"""

import asyncio
import inspect
from mcp.server.fastmcp import FastMCP


async def test_resource_api():
    """Test FastMCP resource API to understand requirements."""
    print("=== FastMCP Resource API Investigation ===\n")
    
    # Create FastMCP instance
    app = FastMCP(name="test")
    
    # Inspect add_resource method signature
    print("🔍 Inspecting add_resource method:")
    try:
        sig = inspect.signature(app.add_resource)
        print(f"  Signature: add_resource{sig}")
        
        # Get parameter info
        params = sig.parameters
        for name, param in params.items():
            print(f"  Parameter '{name}': {param.annotation} (default: {param.default})")
    except Exception as e:
        print(f"  Error inspecting signature: {e}")
    
    # Try to understand what Resource type is expected
    print("\n🔍 Investigating Resource type:")
    try:
        # Try to get the Resource class from mcp module
        import mcp.types
        print(f"  Available in mcp.types: {[attr for attr in dir(mcp.types) if 'Resource' in attr]}")
    except Exception as e:
        print(f"  Error importing mcp.types: {e}")
    
    try:
        # Try different import paths
        from mcp.server.models import Resource
        print(f"  Found Resource in mcp.server.models: {Resource}")
        print(f"  Resource attributes: {[attr for attr in dir(Resource) if not attr.startswith('_')]}")
    except Exception as e:
        print(f"  mcp.server.models.Resource not found: {e}")
    
    try:
        from mcp.types import Resource
        print(f"  Found Resource in mcp.types: {Resource}")
        print(f"  Resource attributes: {[attr for attr in dir(Resource) if not attr.startswith('_')]}")
    except Exception as e:
        print(f"  mcp.types.Resource not found: {e}")
    
    # Try to create a simple resource
    print("\n🔍 Attempting to create and register a test resource:")
    try:
        # Check what happens when we try different resource objects
        
        # Try 1: Simple dict
        print("  Try 1: Simple dict resource")
        try:
            test_resource = {
                "name": "test_resource",
                "uri": "test://resource",
                "description": "Test resource"
            }
            app.add_resource(test_resource)
            print("  ✓ Dict resource accepted")
        except Exception as e:
            print(f"  ❌ Dict resource failed: {e}")
        
        # Try 2: Using @resource decorator to understand the expected structure
        print("  Try 2: Using @resource decorator")
        try:
            @app.resource("test://decorated")
            async def test_decorated_resource():
                return "test content"
            
            print("  ✓ Decorated resource accepted")
        except Exception as e:
            print(f"  ❌ Decorated resource failed: {e}")
        
        # Try 3: Check what resources are registered
        resources = await app.list_resources()
        print(f"  📋 Resources after registration attempts: {len(resources)}")
        for resource in resources:
            print(f"    - {resource}")
            
    except Exception as e:
        print(f"  ❌ Error in resource registration test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_resource_api())