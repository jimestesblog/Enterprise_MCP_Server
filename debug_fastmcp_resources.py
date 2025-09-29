#!/usr/bin/env python3
"""
Debug script to investigate FastMCP's resource handling.

This script will examine how FastMCP stores and exposes resources,
particularly parameterized ones.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP


async def debug_fastmcp_resources():
    """Debug FastMCP resource registration and listing."""
    print("=== Debugging FastMCP Resource Handling ===\n")
    
    # Create a test FastMCP app
    app = FastMCP(name="TEST")
    
    print("1. Testing basic resource registration:")
    
    # Test 1: Non-parameterized resource
    @app.resource("test://basic")
    async def basic_resource():
        return "basic content"
    
    # Test 2: Parameterized resource
    @app.resource("test://param/{id}")
    async def param_resource(id: str):
        return f"parameterized content for {id}"
    
    print("✓ Registered basic and parameterized resources")
    
    # Check what resources are listed
    resources = await app.list_resources()
    print(f"\n2. Resources found via list_resources(): {len(resources)}")
    
    for resource in resources:
        print(f"  - Name: {resource.name}")
        print(f"    URI: {resource.uri}")
        print(f"    Description: {resource.description}")
        print(f"    MIME Type: {resource.mimeType}")
        print()
    
    # Check what templates are listed (parameterized resources might be templates)
    try:
        templates = await app.list_templates()
        print(f"\n2b. Templates found via list_templates(): {len(templates)}")
        
        for template in templates:
            print(f"  - Name: {template.name}")
            print(f"    URI: {template.uriTemplate}")
            print(f"    Description: {template.description}")
            print(f"    MIME Type: {template.mimeType}")
            print()
    except Exception as e:
        print(f"\n2b. Error calling list_templates(): {e}")
    
    # Check internal resource manager
    print("3. Examining internal FastMCP structure:")
    
    if hasattr(app, '_resource_manager'):
        rm = app._resource_manager
        print(f"✓ Found _resource_manager: {type(rm)}")
        
        # Check what methods it has
        methods = [attr for attr in dir(rm) if not attr.startswith('_')]
        print(f"  Available methods: {methods}")
        
        if hasattr(rm, 'resources'):
            print(f"  Internal resources count: {len(rm.resources)}")
            for name, resource in rm.resources.items():
                print(f"    - {name}: {type(resource)}")
        
        if hasattr(rm, 'list_resources'):
            try:
                # ResourceManager methods are not async
                internal_resources = rm.list_resources()
                print(f"  Direct resource manager resources: {len(internal_resources)}")
                for res in internal_resources:
                    print(f"    - {res.name}: {res.uri}")
            except Exception as e:
                print(f"  Error calling rm.list_resources(): {e}")
        
        if hasattr(rm, 'list_templates'):
            try:
                internal_templates = rm.list_templates()
                print(f"  Direct resource manager templates: {len(internal_templates)}")
                for template in internal_templates:
                    # Check what attributes the template actually has
                    template_attrs = [attr for attr in dir(template) if not attr.startswith('_')]
                    print(f"    - {template.name}")
                    print(f"      Available attributes: {template_attrs}")
                    
                    # Try common attribute names for URI template
                    uri_attr = None
                    for attr_name in ['uriTemplate', 'uri_template', 'uri', 'template', 'pattern']:
                        if hasattr(template, attr_name):
                            uri_attr = getattr(template, attr_name)
                            print(f"      URI ({attr_name}): {uri_attr}")
                            break
                    
                    if uri_attr is None:
                        print(f"      URI: <could not determine URI attribute>")
            except Exception as e:
                print(f"  Error calling rm.list_templates(): {e}")
    else:
        print("❌ No _resource_manager found")
        
        # Check other resource-related attributes
        resource_attrs = [attr for attr in dir(app) if 'resource' in attr.lower()]
        print(f"  Resource-related attributes: {resource_attrs}")
    
    return len(resources)


async def test_specific_parameterized_case():
    """Test the specific case that's failing."""
    print("\n=== Testing Specific Parameterized Case ===")
    
    app = FastMCP(name="USECASEY")
    
    # Register the exact same way our factory does
    resource_uri = "mcp://sampledata/{client}/"
    resource_name = "sample_parameterized_resource"
    resource_description = "sample parameterized resource."
    resource_mime_type = "text/plain"
    
    print(f"Registering: {resource_name} at {resource_uri}")
    
    try:
        @app.resource(resource_uri, name=resource_name, description=resource_description, mime_type=resource_mime_type)
        async def resource_handler(client: str):
            return f"Test content for client: {client}"
        
        print("✓ Registration successful")
        
        # Check if it appears in the list
        resources = await app.list_resources()
        print(f"Resources found: {len(resources)}")
        
        for resource in resources:
            print(f"  - {resource.name}: {resource.uri}")
            if resource.name == resource_name:
                print("    ✅ Found our parameterized resource!")
                return True
        
        print("    ❌ Our parameterized resource not found in list")
        return False
        
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return False


async def main():
    """Run all debug tests."""
    print("=== FastMCP Resource Debug Session ===\n")
    
    # Test basic FastMCP resource handling
    basic_count = await debug_fastmcp_resources()
    
    # Test our specific case
    specific_success = await test_specific_parameterized_case()
    
    print(f"\n=== Debug Summary ===")
    print(f"Basic resources found: {basic_count}")
    print(f"Specific case success: {specific_success}")
    
    if basic_count > 0 and specific_success:
        print("✅ FastMCP resource handling appears to work correctly")
        return 0
    else:
        print("❌ Issues found with FastMCP resource handling")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)