"""
Server factory for MCP Server.

This module provides the ServerFactory class that handles
domain and tool registration using the new modular architecture.
"""

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from ..utils.strings import slugify
from ..utils.imports import import_from_path
from ..core.exceptions import ToolRegistrationError, ConfigurationError
from ..core.schemas import build_schema_from_tool_parameters
from ..resources.registry import ResourceRegistrationError
from ..core.auth_config import AuthConfig
from ..core.auth_middleware import AuthenticationManager


class ServerFactory:
    """
    Factory for creating and registering MCP server components.
    
    This replaces the old ToolFactory with improved error handling
    and cleaner separation of concerns.
    """

    def __init__(self, auth_config: Optional[AuthConfig] = None) -> None:
        """
        Initialize ServerFactory with optional authentication configuration.
        
        Args:
            auth_config: Authentication configuration for domain-specific JWT validation
        """
        self.auth_config = auth_config
        self.auth_manager = AuthenticationManager(auth_config) if auth_config else None

    def ensure_domains(self, app, domains: List[Dict[str, Any]], session_managers: List[Any]) -> Dict[str, FastMCP]:
        """
        Pre-create FastMCP apps for declared domains and mount them under /mcp/{slug}.
        
        Args:
            app: FastAPI application
            domains: List of domain configurations
            session_managers: List to collect session managers
            
        Returns:
            Dictionary mapping domain name to FastMCP instance
        """
        domain_apps: Dict[str, FastMCP] = {}
        
        # Initialize detailed domain information storage
        if not hasattr(app.state, 'domain_details'):
            app.state.domain_details = {}
        
        for d in domains or []:
            name = str(d.get("Name") or d.get("name") or "default")
            description = str(d.get("Description") or d.get("description") or "")
            
            slug = slugify(name)
            
            try:
                mcp = FastMCP(name=name, streamable_http_path="/")
                subapp = mcp.streamable_http_app()
                
                # Apply authentication middleware if configured
                if self.auth_manager and self.auth_manager.is_authentication_enabled(name):
                    auth_middleware = self.auth_manager.create_middleware(subapp, name)
                    subapp.add_middleware(type(auth_middleware), **auth_middleware.__dict__)
                
                app.mount(f"/mcp/{slug}", subapp)
                app.state.mcp_mounts.append({
                    "name": name, 
                    "slug": slug, 
                    "path": f"/mcp/{slug}",
                    "description": description,
                    "auth_enabled": self.auth_manager.is_authentication_enabled(name) if self.auth_manager else False
                })
                
                # Initialize detailed domain information
                app.state.domain_details[name] = {
                    "name": name,
                    "slug": slug,
                    "path": f"/mcp/{slug}",
                    "description": description,
                    "auth_enabled": self.auth_manager.is_authentication_enabled(name) if self.auth_manager else False,
                    "tools": [],
                    "resources": []
                }
                
                domain_apps[name] = mcp
                session_managers.append(mcp.session_manager)
                
            except Exception as e:
                raise ConfigurationError(f"Failed to create domain '{name}': {e}")
        
        return domain_apps

    def register_tool_classes(self, app, domain_apps: Dict[str, FastMCP], 
                            tool_classes: List[Dict[str, Any]], 
                            session_managers: List[Any]) -> None:
        """
        Register tools on their respective domain FastMCP instances.
        Creates missing domains lazily when referenced by tool_classes.
        
        Args:
            app: FastAPI application
            domain_apps: Existing domain applications
            tool_classes: List of tool class configurations
            session_managers: List to collect session managers
        """
        for tc in tool_classes or []:
            try:
                self._register_single_tool_class(app, domain_apps, tc, session_managers)
            except Exception as e:
                tool_name = tc.get("class_name") or tc.get("name") or "unknown"
                raise ToolRegistrationError(f"Failed to register tool '{tool_name}': {e}")

    def _register_single_tool_class(self, app, domain_apps: Dict[str, FastMCP], 
                                  tc: Dict[str, Any], session_managers: List[Any]) -> None:
        """Register a single tool class."""
        # Extract configuration
        domain_name = str(tc.get("Domain") or tc.get("domain") or "default")
        class_type = str(tc.get("class_type") or "").strip()
        class_name_prefix = str(tc.get("class_name") or tc.get("name") or "tool").strip()
        class_description = str(tc.get("class_description") or tc.get("description") or "").strip()
        init_params = tc.get("class_initialization_params") or tc.get("initialization_params") or {}

        if not class_type:
            raise ConfigurationError("Missing class_type in tool_classes entry")

        # Ensure domain exists
        if domain_name not in domain_apps:
            self._create_missing_domain(app, domain_name, domain_apps, session_managers)

        mcp_app = domain_apps[domain_name]

        # Import and instantiate tool class
        try:
            cls = import_from_path(class_type)
        except Exception as e:
            raise ConfigurationError(f"Cannot import tool class '{class_type}': {e}")

        # Prepare initialization parameters
        if isinstance(init_params, dict):
            conf = dict(init_params)
            conf.setdefault("name", class_name_prefix)
            if class_description:
                conf.setdefault("description", class_description)
            init_params = conf

        # Create tool instance
        try:
            instance = cls(init_params)
        except TypeError:
            # Fallback for classes that expect **kwargs
            try:
                instance = cls(**init_params)
            except Exception as e:
                raise ToolRegistrationError(f"Cannot instantiate {class_type}: {e}")
        except Exception as e:
            raise ToolRegistrationError(f"Cannot instantiate {class_type}: {e}")

        # Store tool class information in domain details
        if hasattr(app.state, 'domain_details') and domain_name in app.state.domain_details:
            tool_class_info = {
                "name": class_name_prefix,
                "type": class_type,
                "description": class_description,
                "tools": []
            }
            
            # Register tool methods and collect tool information
            for tool_def in tc.get("tools", []) or []:
                tool_info = self._register_tool_method(instance, tool_def, class_name_prefix, 
                                                     class_description, mcp_app, app, domain_name)
                if tool_info:
                    tool_class_info["tools"].append(tool_info)
            
            # Add the tool class info to the domain
            app.state.domain_details[domain_name]["tools"].append(tool_class_info)
        else:
            # Fallback to original behavior if domain_details not available
            for tool_def in tc.get("tools", []) or []:
                self._register_tool_method(instance, tool_def, class_name_prefix, 
                                         class_description, mcp_app, app, domain_name)

    def _create_missing_domain(self, app, domain_name: str, 
                             domain_apps: Dict[str, FastMCP], 
                             session_managers: List[Any]) -> None:
        """Create a domain that was referenced but not declared."""
        slug = slugify(domain_name)
        
        try:
            mcp = FastMCP(name=domain_name, streamable_http_path="/")
            subapp = mcp.streamable_http_app()
            
            # Apply authentication middleware if configured
            if self.auth_manager and self.auth_manager.is_authentication_enabled(domain_name):
                auth_middleware = self.auth_manager.create_middleware(subapp, domain_name)
                subapp.add_middleware(type(auth_middleware), **auth_middleware.__dict__)
            
            app.mount(f"/mcp/{slug}", subapp)
            app.state.mcp_mounts.append({
                "name": domain_name, 
                "slug": slug, 
                "path": f"/mcp/{slug}",
                "description": f"Auto-created domain for {domain_name}",
                "auth_enabled": self.auth_manager.is_authentication_enabled(domain_name) if self.auth_manager else False
            })
            
            # Initialize detailed domain information for auto-created domain
            if not hasattr(app.state, 'domain_details'):
                app.state.domain_details = {}
            app.state.domain_details[domain_name] = {
                "name": domain_name,
                "slug": slug,
                "path": f"/mcp/{slug}",
                "description": f"Auto-created domain for {domain_name}",
                "auth_enabled": self.auth_manager.is_authentication_enabled(domain_name) if self.auth_manager else False,
                "tools": [],
                "resources": []
            }
            
            domain_apps[domain_name] = mcp
            session_managers.append(mcp.session_manager)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create missing domain '{domain_name}': {e}")

    def _register_tool_method(self, instance: Any, tool_def: Dict[str, Any], 
                            class_name_prefix: str, class_description: str, 
                            mcp_app: FastMCP, app=None, domain_name=None) -> Optional[Dict[str, Any]]:
        """Register a single tool method and return tool information."""
        import logging
        import json
        
        func_name = str(tool_def.get("function") or "").strip()
        func_desc = str(tool_def.get("function_description") or class_description)
        
        if not func_name:
            return None
        
        action = func_name.lstrip("_")
        tool_name = f"{class_name_prefix}.{action}"
        
        # Create wrapper function
        wrapper = self._make_invoke_wrapper(instance, func_name, action)
        
        # Register with MCP app
        mcp_app.add_tool(wrapper, name=tool_name, description=func_desc)
        
        # Prepare tool information for return
        tool_info = {
            "name": tool_name,
            "function": func_name,
            "description": func_desc,
            "parameters": tool_def.get("tool_parameters", [])
        }
        
        # Apply parameter schema if provided
        tool_params = tool_def.get("tool_parameters")
        if tool_params:
            try:
                schema = build_schema_from_tool_parameters(tool_params)
                tool_mgr = getattr(mcp_app, "_tool_manager", None)
                if tool_mgr is not None:
                    registered = tool_mgr.get_tool(tool_name)
                    if registered is not None:
                        registered.parameters = schema
            except Exception:
                # Schema application is best-effort
                pass
        
        # Apply output schema if provided
        tool_output_schema = tool_def.get("tool_output_schema")
        if tool_output_schema:
            try:
                # Check if tool class has implicit output schema method
                implicit_schema_method = getattr(instance, f"get_output_schema_{action}", None) or \
                                       getattr(instance, "get_output_schema", None)
                
                if implicit_schema_method and callable(implicit_schema_method):
                    logging.warning(f"Tool {tool_name}: Explicit output schema defined in configuration "
                                  f"overrides implicit schema from tool class method")
                
                # Apply explicit output schema to the registered tool
                tool_mgr = getattr(mcp_app, "_tool_manager", None)
                if tool_mgr is not None:
                    registered = tool_mgr.get_tool(tool_name)
                    if registered is not None:
                        # Store output schema in tool metadata
                        if not hasattr(registered, '_output_schema'):
                            registered._output_schema = tool_output_schema
                        
            except Exception as e:
                logging.warning(f"Failed to apply output schema for tool {tool_name}: {e}")
        
        return tool_info

    def _make_invoke_wrapper(self, instance: Any, func_name: str, action_name: str):
        """
        Create a wrapper for tool method invocation.
        
        This is a simplified version that prefers the exact function name,
        then falls back to the action name.
        """
        # Try exact function name first, then action name
        method = getattr(instance, func_name, None) or getattr(instance, action_name, None)
        
        if callable(method):
            return method
        
        # Explicit failure if nothing is callable
        raise ToolRegistrationError(
            f"No callable method found for '{action_name}' on {type(instance).__name__}"
        )

    def register_resource_classes(self, app, domain_apps: Dict[str, FastMCP], 
                                resource_classes: List[Dict[str, Any]], 
                                session_managers: List[Any]) -> None:
        """
        Register resource classes on their respective domain FastMCP instances.
        Creates missing domains lazily when referenced by resource_classes.
        
        Args:
            app: FastAPI application
            domain_apps: Existing domain applications
            resource_classes: List of resource class configurations
            session_managers: List to collect session managers
        """
        for rc in resource_classes or []:
            try:
                self._register_single_resource_class(app, domain_apps, rc, session_managers)
            except Exception as e:
                resource_name = rc.get("class_name") or rc.get("name") or "unknown"
                raise ResourceRegistrationError(f"Failed to register resource '{resource_name}': {e}")

    def _register_single_resource_class(self, app, domain_apps: Dict[str, FastMCP], 
                                      rc: Dict[str, Any], session_managers: List[Any]) -> None:
        """Register a single resource class."""
        # Extract configuration
        domain_name = str(rc.get("Domain") or rc.get("domain") or "default")
        class_type = str(rc.get("class_type") or "").strip()
        class_name_prefix = str(rc.get("class_name") or rc.get("name") or "resource").strip()
        class_description = str(rc.get("class_description") or rc.get("description") or "").strip()
        init_params = rc.get("class_initialization_params") or rc.get("initialization_params") or {}
        resources = rc.get("resources", [])

        if not class_type:
            raise ConfigurationError("Missing class_type in resource_classes entry")

        # Ensure domain exists
        if domain_name not in domain_apps:
            self._create_missing_domain(app, domain_name, domain_apps, session_managers)

        mcp_app = domain_apps[domain_name]

        # Import and instantiate resource class
        try:
            cls = import_from_path(class_type)
        except Exception as e:
            raise ConfigurationError(f"Cannot import resource class '{class_type}': {e}")

        # Prepare initialization parameters
        if isinstance(init_params, dict):
            conf = dict(init_params)
            conf.setdefault("name", class_name_prefix)
            if class_description:
                conf.setdefault("description", class_description)
            # Add resources to params for the class
            if "params" not in conf or conf["params"] is None:
                conf["params"] = {}
            conf["params"]["resources"] = resources
            init_params = conf

        # Create resource instance
        try:
            instance = cls(init_params)
        except TypeError:
            # Fallback for classes that expect **kwargs
            try:
                instance = cls(**init_params)
            except Exception as e:
                raise ResourceRegistrationError(f"Cannot instantiate {class_type}: {e}")
        except Exception as e:
            raise ResourceRegistrationError(f"Cannot instantiate {class_type}: {e}")

        # Store resource class information in domain details
        if hasattr(app.state, 'domain_details') and domain_name in app.state.domain_details:
            resource_class_info = {
                "name": class_name_prefix,
                "type": class_type,
                "description": class_description,
                "resources": resources  # Store the resource configurations
            }
            
            # Add the resource class info to the domain
            app.state.domain_details[domain_name]["resources"].append(resource_class_info)
        
        # Register resources with MCP app
        self._register_resource_methods(instance, class_name_prefix, class_description, mcp_app)

    def _register_resource_methods(self, instance: Any, class_name_prefix: str, 
                                 class_description: str, mcp_app: FastMCP) -> None:
        """Register resource methods with the MCP app using proper MCP protocol."""
        from mcp.types import Resource
        from urllib.parse import urlparse
        import logging
        
        # Get all resources managed by this class
        if hasattr(instance, 'get_resources'):
            try:
                resources = instance.get_resources()
                for resource_def in resources:
                    resource_name = resource_def.get("name")
                    resource_uri = resource_def.get("uri", "")
                    resource_description = resource_def.get("description", "")
                    resource_mime_type = resource_def.get("mimeType", "text/plain")
                    
                    if resource_name:
                        try:
                            # Handle parameterized URIs by creating a valid base URI
                            if resource_uri.startswith('//'):
                                # Convert relative URIs to valid scheme-based URIs
                                resource_uri = f"mcp:{resource_uri}"
                            elif not resource_uri.startswith(('http://', 'https://', 'file://', 'mcp://')):
                                # Ensure URI has a valid scheme
                                resource_uri = f"mcp://{resource_uri}"
                            
                            # Check if this resource has parameters (template URI)
                            import re
                            uri_params = set(re.findall(r'\{(\w+)\}', resource_uri))
                            
                            # Register the resource handler for content retrieval using decorator approach
                            # Handle parameterized vs non-parameterized resources differently
                            if uri_params:
                                # For parameterized resources, create a handler with explicit parameters
                                # Build the function signature dynamically to match URI parameters
                                param_names = list(uri_params)
                                
                                if len(param_names) == 1 and 'client' in param_names:
                                    # Special case for the common 'client' parameter
                                    @mcp_app.resource(resource_uri, name=resource_name, description=resource_description, mime_type=resource_mime_type)
                                    async def resource_handler(client: str):
                                        """Handler for client-parameterized resource content retrieval."""
                                        try:
                                            if hasattr(instance, 'get_resource_content'):
                                                params = {'client': client}
                                                content = await instance.get_resource_content(resource_name, params)
                                                return content
                                            else:
                                                content = await instance.get_content({'client': client})
                                                return content
                                        except Exception as e:
                                            logging.error(f"Error retrieving content for parameterized resource {resource_name}: {e}")
                                            return f"Error retrieving resource content: {e}"
                                else:
                                    # For other parameter combinations, use a generic approach
                                    # Create a function that dynamically accepts the required parameters
                                    def create_handler():
                                        async def resource_handler(**kwargs):
                                            try:
                                                if hasattr(instance, 'get_resource_content'):
                                                    params = {k: v for k, v in kwargs.items() if k in uri_params}
                                                    content = await instance.get_resource_content(resource_name, params)
                                                    return content
                                                else:
                                                    content = await instance.get_content(kwargs)
                                                    return content
                                            except Exception as e:
                                                logging.error(f"Error retrieving content for parameterized resource {resource_name}: {e}")
                                                return f"Error retrieving resource content: {e}"
                                        
                                        # Set the function signature to match URI parameters
                                        import inspect
                                        from typing import get_type_hints
                                        
                                        # Create parameters for the function signature
                                        sig_params = []
                                        for param_name in param_names:
                                            sig_params.append(inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str))
                                        
                                        resource_handler.__signature__ = inspect.Signature(sig_params)
                                        return resource_handler
                                    
                                    handler = create_handler()
                                    mcp_app.resource(resource_uri, name=resource_name, description=resource_description, mime_type=resource_mime_type)(handler)
                            else:
                                # For non-parameterized resources, use the original approach
                                @mcp_app.resource(resource_uri, name=resource_name, description=resource_description, mime_type=resource_mime_type)
                                async def resource_handler():
                                    """Handler for non-parameterized resource content retrieval."""
                                    try:
                                        if hasattr(instance, 'get_resource_content'):
                                            content = await instance.get_resource_content(resource_name, {})
                                            return content
                                        else:
                                            content = await instance.get_content({})
                                            return content
                                    except Exception as e:
                                        logging.error(f"Error retrieving content for resource {resource_name}: {e}")
                                        return f"Error retrieving resource content: {e}"
                            
                            logging.info(f"Successfully registered MCP resource: {resource_name}")
                            
                        except Exception as e:
                            logging.error(f"Failed to register resource {resource_name}: {e}")
                            
            except Exception as e:
                # Resource registration is best-effort
                import logging
                logging.warning(f"Failed to register resources for {class_name_prefix}: {e}")

    def _make_resource_handler(self, instance: Any, resource_name: str):
        """Create a handler for a specific resource."""
        async def resource_handler(parameters=None):
            if hasattr(instance, 'get_resource_content'):
                return await instance.get_resource_content(resource_name, parameters)
            else:
                return await instance.get_content(parameters)
        
        return resource_handler