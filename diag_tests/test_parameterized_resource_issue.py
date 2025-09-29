#!/usr/bin/env python3
"""
Test script to diagnose the sample_parameterized_resource issue.

This script will check if the parameterized resource is being properly
registered and exposed via the MCP protocol in the USECASEY domain.
"""

import asyncio
import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.core.config import load_config, get_default_config_path
from mcp_server.server.app import create_http_app


async def test_parameterized_resource_registration():
    """Test if sample_parameterized_resource is being registered properly."""
    print("=== Testing sample_parameterized_resource Registration ===\n")
    
    try:
        # Load configuration
        config_path = get_default_config_path()
        config = load_config(config_path)
        print(f"✓ Configuration loaded with {len(config.resources)} resource classes")
        
        # Find the ExamplePrivateResources configuration
        private_resource_config = None
        for resource_config in config.resources:
            if resource_config.class_type == "mcp_server.resources.example1.privateresourceexample.ExamplePrivateResources":
                private_resource_config = resource_config
                break
        
        if not private_resource_config:
            print("❌ ExamplePrivateResources configuration not found!")
            return False
        
        print(f"✓ Found ExamplePrivateResources config: {private_resource_config.name}")
        
        # Check if sample_parameterized_resource is in the resources list
        sample_resource = None
        for resource in private_resource_config.resources:
            if resource.name == "sample_parameterized_resource":
                sample_resource = resource
                break
        
        if not sample_resource:
            print("❌ sample_parameterized_resource not found in configuration!")
            return False
        
        print(f"✓ Found sample_parameterized_resource in config:")
        print(f"  - Name: {sample_resource.name}")
        print(f"  - Function: {sample_resource.function}")
        print(f"  - URI: {sample_resource.uri}")
        print(f"  - Access: {sample_resource.access}")
        print(f"  - Parameters: {len(sample_resource.resource_parameters)}")
        
        # Create the app and see what happens during startup
        print("\n🔍 Creating MCP server app...")
        app = create_http_app(config)
        print("✓ Server app created successfully")
        
        # Check what domains were mounted
        if hasattr(app.state, 'mcp_mounts'):
            print(f"✓ MCP mounts found: {len(app.state.mcp_mounts)}")
            for mount in app.state.mcp_mounts:
                print(f"  - {mount['name']}: {mount['path']}")
        else:
            print("❌ No MCP mounts found in app state")
        
        # Try to test the resource class directly
        print("\n🔍 Testing ExamplePrivateResources class directly...")
        from mcp_server.resources.example1.privateresourceexample import ExamplePrivateResources
        
        # Create instance with the same config the server would use
        init_params = private_resource_config.initialization_params or {}
        conf = dict(init_params)
        conf.setdefault("name", private_resource_config.name)
        conf.setdefault("description", private_resource_config.description)
        if "params" not in conf or conf["params"] is None:
            conf["params"] = {}
        conf["params"]["resources"] = [r.dict() for r in private_resource_config.resources]
        
        resource_instance = ExamplePrivateResources(conf)
        print("✓ ExamplePrivateResources instance created")
        
        # Test the get_resources method
        resources = resource_instance.get_resources()
        print(f"✓ get_resources() returned {len(resources)} resources")
        
        for resource_def in resources:
            print(f"  - {resource_def.get('name')}: {resource_def.get('uri')}")
            if resource_def.get('name') == 'sample_parameterized_resource':
                print("    ✓ sample_parameterized_resource found in get_resources() output")
                
                # Test the actual function
                try:
                    content = await resource_instance.get_resource_content(
                        "sample_parameterized_resource", 
                        {"client": "acme"}
                    )
                    print(f"    ✓ Function test successful: '{content}'")
                except Exception as e:
                    print(f"    ❌ Function test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in registration test: {e}")
        traceback.print_exc()
        return False


async def test_mcp_protocol_exposure():
    """Test if the resource is actually exposed via MCP protocol."""
    print("\n=== Testing MCP Protocol Exposure ===")
    
    try:
        # Create a minimal FastMCP app to test resource registration
        from mcp.server.fastmcp import FastMCP
        from mcp_server.server.factory import ServerFactory
        
        # Create USECASEY domain app
        usecasey_app = FastMCP(name="USECASEY")
        
        # Load configuration
        config = load_config(get_default_config_path())
        
        # Use factory to register resources
        factory = ServerFactory()
        
        # Filter for USECASEY resource classes
        usecasey_resources = []
        for resource_config in config.resources:
            if resource_config.domain == "USECASEY":
                usecasey_resources.append(resource_config.dict())
        
        print(f"✓ Found {len(usecasey_resources)} USECASEY resource classes")
        
        # Register resources using the factory method
        try:
            # Create a fake app for mounting (factory needs this)
            from fastapi import FastAPI
            fake_app = FastAPI()
            fake_app.state.mcp_mounts = []
            
            domain_apps = {"USECASEY": usecasey_app}
            session_managers = []
            
            factory.register_resource_classes(
                fake_app, 
                domain_apps, 
                usecasey_resources, 
                session_managers
            )
            print("✓ Resources registered via factory")
            
        except Exception as e:
            print(f"⚠️ Factory registration failed: {e}")
            # Try manual registration as fallback
            print("🔄 Attempting manual registration...")
            
            from mcp_server.resources.example1.privateresourceexample import ExamplePrivateResources
            
            # Find the private resource config
            private_config = None
            for rc in usecasey_resources:
                if "privateresourceexample" in rc.get("class_type", ""):
                    private_config = rc
                    break
            
            if private_config:
                # Create instance
                init_params = private_config.get("class_initialization_params", {})
                if "params" not in init_params or init_params["params"] is None:
                    init_params["params"] = {}
                init_params["params"]["resources"] = private_config.get("resources", [])
                init_params["name"] = private_config.get("class_name", "private_resources")
                
                instance = ExamplePrivateResources(init_params)
                
                # Register resources manually using the fixed method
                factory._register_resource_methods(instance, "example_private_resources", "Example private resource types", usecasey_app)
                print("✓ Manual registration completed")
        
        # Check what resources are now available
        resources = await usecasey_app.list_resources()
        print(f"✓ MCP protocol lists {len(resources)} resources:")
        
        sample_found = False
        for resource in resources:
            print(f"  - {resource.name}: {resource.uri}")
            if resource.name == "sample_parameterized_resource":
                sample_found = True
                print("    ✅ sample_parameterized_resource FOUND in resources!")
        
        # Also check templates (parameterized resources are stored as templates)
        if hasattr(usecasey_app, '_resource_manager') and hasattr(usecasey_app._resource_manager, 'list_templates'):
            try:
                templates = usecasey_app._resource_manager.list_templates()
                print(f"✓ MCP protocol lists {len(templates)} templates:")
                
                for template in templates:
                    uri_template = getattr(template, 'uri_template', 'unknown')
                    print(f"  - {template.name}: {uri_template}")
                    if template.name == "sample_parameterized_resource":
                        sample_found = True
                        print("    ✅ sample_parameterized_resource FOUND in templates!")
            except Exception as e:
                print(f"  ⚠️ Error checking templates: {e}")
        
        if not sample_found:
            print("    ❌ sample_parameterized_resource NOT found in either resources or templates")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error in MCP protocol test: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic tests."""
    print("=== Diagnosing sample_parameterized_resource Issue ===\n")
    
    results = []
    
    # Test resource registration
    results.append(await test_parameterized_resource_registration())
    
    # Test MCP protocol exposure
    results.append(await test_mcp_protocol_exposure())
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ sample_parameterized_resource is working properly!")
        return 0
    else:
        print("❌ Issues found with sample_parameterized_resource")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)