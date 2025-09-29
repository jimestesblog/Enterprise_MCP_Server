"""
Refactored FastAPI application for MCP Server.

This module creates the main FastAPI application using
the new modular architecture.
"""

import os
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI
import uvicorn

from ..core.config import load_config, get_default_config_path, AppConfig
from ..core.auth_config import load_auth_config, get_default_auth_config_path, AuthConfig
from ..core.exceptions import ConfigurationError
from .factory import ServerFactory


def create_http_app(config: Optional[AppConfig] = None, auth_config: Optional[AuthConfig] = None) -> FastAPI:
    """
    Create FastAPI application with MCP server functionality.
    
    Args:
        config: Application configuration
        auth_config: Authentication configuration
        
    Returns:
        FastAPI application instance
    """
    if config is None:
        config = AppConfig()

    # Collect session managers for all domain FastMCPs
    session_managers: list = []

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start all session managers on startup
        stack = AsyncExitStack()
        app.state._exit_stack = stack  # optional: to allow later inspection/cleanup
        for sm in session_managers:
            await stack.enter_async_context(sm.run())
        try:
            yield  # app is running
        finally:
            # Ensure graceful shutdown of all session managers
            await stack.aclose()

    # IMPORTANT: construct FastAPI with the custom lifespan
    app = FastAPI(
        title="MCP Server",
        description="Model Context Protocol Server with Tool Support",
        version="1.0.0",
        lifespan=lifespan
    )

    # Track FastMCP mounts and expose an index endpoint
    app.state.mcp_mounts = []  # list of {name, slug, path}

    @app.get("/mcp")
    async def list_mcp_mounts():
        """List all mounted MCP endpoints with detailed information about tools and resources."""
        # Try to return detailed domain information first
        domain_details = getattr(app.state, "domain_details", None)
        if domain_details is not None and len(domain_details) > 0:
            domains = []
            for domain_name, details in domain_details.items():
                domains.append({
                    "name": details["name"],
                    "slug": details["slug"], 
                    "path": details["path"],
                    "description": details["description"],
                    "auth_enabled": details["auth_enabled"],
                    "tools": details["tools"],
                    "resources": details["resources"]
                })
            return {"domains": domains}
        
        # Fallback to basic mount information
        mounts = getattr(app.state, "mcp_mounts", None)
        if mounts is not None and len(mounts) > 0:
            return {"mounts": mounts}
        
        # Final fallback: introspect router mounts in case state isn't set or ran differently
        try:
            from starlette.routing import Mount
            fallback = []
            for route in app.router.routes:
                if isinstance(route, Mount) and route.path.startswith("/mcp/"):
                    slug = route.path.removeprefix("/mcp/").strip("/")
                    fallback.append({"name": slug, "slug": slug, "path": route.path})
            return {"mounts": fallback}
        except Exception:
            return {"mounts": []}

    # Health/readiness endpoints
    @app.get("/healthz")
    async def healthz():
        """Health check endpoint."""
        return {"ok": True, "status": "healthy"}

    @app.get("/readyz")
    async def readyz():
        """Readiness check endpoint."""
        return {"ok": True, "status": "ready"}

    # Initialize server factory and setup domains/tools
    factory = ServerFactory(auth_config)
    
    try:
        # Setup domains from configuration
        if config.domains or config.Domains:
            domains_data = config.Domains or [d.dict() for d in config.domains]
            domain_apps = factory.ensure_domains(app, domains_data, session_managers)
        else:
            domain_apps = {}
        
        # Setup tools from configuration
        if config.tools or config.mcp_classes:
            tools_data = config.mcp_classes or [t.dict() for t in config.tools]
            factory.register_tool_classes(app, domain_apps, tools_data, session_managers)
        
        # Setup resources from configuration
        if config.resources:
            resources_data = [r.dict() for r in config.resources]
            factory.register_resource_classes(app, domain_apps, resources_data, session_managers)
            
    except Exception as e:
        raise ConfigurationError(f"Failed to setup application: {e}")

    return app


def run():
    """
    Application entrypoint.
    
    Builds the FastAPI app and runs uvicorn server.
    Reads optional CONFIG_PATH env var for tools configuration.
    """
    try:
        # Load configuration
        config_path = get_default_config_path()
        config = load_config(config_path) if config_path else AppConfig()
        
        # Load authentication configuration
        auth_config_path = get_default_auth_config_path()
        auth_config = load_auth_config(auth_config_path) if auth_config_path else AuthConfig()
        
        # Create application
        app = create_http_app(config, auth_config)
        
        # Run server
        port = int(os.getenv("HEALTH_PORT", "8080"))
        host = os.getenv("HOST", "127.0.0.1")
        
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
        
    except Exception as e:
        print(f"Failed to start server: {e}")
        raise