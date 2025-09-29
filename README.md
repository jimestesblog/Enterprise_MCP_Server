# MCP Server - Model Context Protocol Server

**Last Updated: September 29, 2025**

 Example of a  highly configurable, deployment-ready Model Context Protocol (MCP) server built with Python and FastAPI. This server provides a **fully modular architecture** where tools and resources can be developed as **external packages**, installed independently, and configured dynamically without code changes. The server enables seamless communication with MCP-compatible clients through its extensible plugin system.

## Features

- **🏗️ Modular Architecture**: Clean separation of concerns with dedicated modules for core functionality, server components, tools, and utilities
- **⚙️ Dynamic Tool Loading**: Configure tools via YAML/JSON without code changes
- **🔒 Secure Configuration**: Environment variable-based API key management
- **🚀 Deployment Ready**: Health endpoints, Docker support, and Kubernetes deployment
- **🧰 Built-in Tools**: Weather forecasting, financial data (Plaid), and extensible tool framework
- **📁 Dynamic Resources**: Support for public HTTP resources and internal MCP server resources with parameterization
- **📡 FastAPI Integration**: RESTful endpoints with automatic OpenAPI documentation
- **🐳 Container Support**: Docker and Kubernetes deployment configurations

## Getting Started

### Quick Start

Get your MCP Server running in minutes:

#### 1. Installation

**Option A: Clone and Install from Source**
```bash
# Clone the repository
git clone <repository-url>
cd MCPServer

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Option B: Install as Package** (Coming Soon. when available on PyPI)
```bash
pip install mcp-server
```

#### 2. Configuration

Create or modify your configuration file:

```bash
# Copy example configuration
cp config/tools.yaml.example config/tools.yaml

# Edit configuration with your API keys and settings
notepad config/tools.yaml  # Windows
nano config/tools.yaml     # Linux/macOS
```

Example basic configuration:
```yaml
Domains:
  - Name: WEATHER
    Description: Weather information tools

mcp_classes:
  - Domain: WEATHER
    class_type: mcp_server.tools.weather.google_weather.GoogleWeatherTool
    class_name: google_weather
    class_description: Google Weather API integration
    class_initialization_params:
      params:
        api_key: "${GOOGLE_WEATHER_API_KEY}"
    tools:
      - function: current_conditions
        function_description: Get current weather conditions
        tool_parameters:
          - name: latitude
            description: Latitude coordinate
            allowed_values: string
          - name: longitude
            description: Longitude coordinate
            allowed_values: string
```

#### 3. Environment Variables

Set up required environment variables:

```bash
# Windows
set GOOGLE_WEATHER_API_KEY=your-api-key-here
set LOG_LEVEL=info

# Linux/macOS
export GOOGLE_WEATHER_API_KEY=your-api-key-here
export LOG_LEVEL=info
```

#### 4. Run the Server

Start the MCP Server:

```bash
# Run directly
python -m mcp_server

# Or with custom configuration
python -m mcp_server --config config/tools.yaml

# Or with specific port
python -m mcp_server --port 8080
```

#### 5. Verify Installation

Test that your server is running:

```bash
# Check health endpoint
curl http://localhost:3000/health

# List available tools
curl http://localhost:3000/tools

# Test MCP endpoint
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

### Docker Installation

Run with Docker for containerized deployment:

```bash
# Build the image
docker build -t mcp-server .

# Run with environment variables
docker run -d \
  --name mcp-server \
  -p 3000:3000 \
  -e GOOGLE_WEATHER_API_KEY=your-api-key \
  -e LOG_LEVEL=info \
  mcp-server

# Check logs
docker logs mcp-server
```

### Kubernetes Deployment

Deploy to Kubernetes cluster:

```bash
# Create namespace
kubectl create namespace mcp-server

# Apply configuration with your API keys
kubectl apply -f k8s/deployment.yaml -n mcp-server

# Check deployment status
kubectl get pods -n mcp-server

# Access via port forward
kubectl port-forward service/mcp-server 3000:3000 -n mcp-server
```

### Adding Your First Custom Tool

1. **Create a new tool file**:
```python
# my_custom_tool.py
from mcp_server.tools.enhanced_base import Tool, ToolConfig
from typing import Dict, Any

class HelloWorldTool(Tool):
    async def execute(self, **kwargs) -> Dict[str, Any]:
        name = kwargs.get("name", "World")
        return {"message": f"Hello, {name}!"}
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"}
            }
        }
```

2. **Add to configuration**:
```yaml
mcp_classes:
  - Domain: DEMO
    class_type: my_custom_tool.HelloWorldTool
    class_name: hello_world
    class_description: Simple hello world tool
    tools:
      - function: execute
        function_description: Say hello
        tool_parameters:
          - name: name
            description: Name to greet
            allowed_values: string
```

3. **Restart server and test**:
```bash
# Test your new tool
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "hello_world.execute",
      "arguments": {"name": "MCP User"}
    }
  }'
```

### Troubleshooting Common Issues

**Server won't start**:
- Check that all environment variables are set
- Verify configuration file syntax (YAML format)
- Ensure no port conflicts (default port 3000)

**Tool loading fails**:
- Verify `class_type` paths are correct
- Check that tool classes inherit from `Tool` base class
- Ensure all dependencies are installed

**API calls fail**:
- Verify API keys are valid and properly configured
- Check network connectivity and firewall settings
- Review rate limits and API quotas

**Need help?**:
- Check server logs: `docker logs mcp-server` or console output
- Review configuration against examples in this README
- Validate JSON/YAML syntax in configuration files

## Architecture

The MCP Server follows a clean, modular architecture designed for maintainability, security, and extensibility:

```
mcp_server/
├── core/                    # Core functionality
│   ├── config.py           # Centralized configuration management with Pydantic
│   ├── exceptions.py       # Custom exception hierarchy
│   └── schemas.py          # JSON schema builders for tool parameters
├── server/                  # Server components
│   ├── app.py             # FastAPI application and server lifecycle
│   └── factory.py         # ServerFactory for domain and tool registration
├── tools/                   # Tool implementations
│   ├── enhanced_base.py    # Abstract base classes with proper typing
│   ├── registry.py         # Simplified tool registration system
│   ├── base.py            # Legacy base classes (backward compatibility)
│   ├── plaid.py           # Financial data tool (Plaid API)
│   └── weather/            # Weather tools
│       └── google_weather.py # Google Weather API integration
└── utils/                   # Utility functions
    ├── strings.py          # String manipulation utilities
    └── imports.py          # Dynamic import helpers
```

### Key Architectural Components

#### Configuration Management (`core/config.py`)
- **Pydantic-based validation**: Type-safe configuration with automatic validation
- **Environment variable expansion**: Secure API key management using `${VARIABLE_NAME}` syntax
- **Legacy compatibility**: Supports both new and old configuration formats
- **Centralized loading**: Single point of configuration management

#### Server Factory (`server/factory.py`)
- **Domain management**: Automatic creation and mounting of MCP domains
- **Tool registration**: Dynamic tool instantiation and registration
- **Error handling**: Comprehensive error reporting with context
- **Session management**: Proper lifecycle management for MCP sessions

#### Tool Registry (`tools/registry.py`)
- **Dynamic registration**: Runtime tool class registration from configuration
- **Type safety**: Ensures all tools inherit from proper base classes
- **Instance management**: Centralized tool instance lifecycle
- **Import utilities**: Safe dynamic imports with error handling

## Developing External Packages

The MCP Server's modular architecture enables you to develop tools and resources as **external packages** that can be installed independently and configured dynamically. This approach promotes code reusability, maintainability, and allows for distributed development of MCP components.

### Why External Packages?

- **🔌 Plug-and-Play**: Install only the tools you need
- **📦 Distribution**: Share tools via PyPI or private repositories  
- **🔄 Versioning**: Independent versioning for each tool package
- **👥 Collaboration**: Teams can develop tools independently
- **🧪 Testing**: Isolated testing environments per package
- **🔒 Security**: Minimal dependencies and controlled access

### Package Structure

A typical external MCP tool package follows this structure:

```
my-mcp-tools/
├── setup.py                    # Package configuration
├── README.md                   # Package documentation
├── requirements.txt            # Dependencies
├── my_mcp_tools/              # Package root
│   ├── __init__.py
│   ├── tools/                 # Tool implementations
│   │   ├── __init__.py
│   │   ├── custom_api.py      # Custom API tool
│   │   └── data_processor.py  # Data processing tool
│   └── resources/             # Resource implementations
│       ├── __init__.py
│       └── external_data.py   # External data resource
├── tests/                     # Package tests
│   ├── test_tools.py
│   └── test_resources.py
└── config/                    # Example configurations
    └── tools.yaml.example
```

### Creating an External Tool Package

#### 1. Package Setup (`setup.py`)

```python
from setuptools import setup, find_packages

setup(
    name="my-custom-mcp-tools",
    version="1.0.0",
    description="Custom MCP tools for XYZ integration",
    author="Your Name",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "mcp-server>=2.0.0",  # Base MCP server dependency
        "httpx>=0.24.0",      # For HTTP requests
        "pydantic>=2.0.0",    # For data validation
        # Add your specific dependencies
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
```

#### 2. Tool Implementation

```python
# my_mcp_tools/tools/custom_api.py
from mcp_server.tools.enhanced_base import Tool, ToolConfig
from typing import Dict, Any
import httpx

class CustomAPITool(Tool):
    """Custom API integration tool."""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.api_key = config.params.get("api_key")
        self.base_url = config.params.get("base_url")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute API call with given parameters."""
        endpoint = kwargs.get("endpoint", "")
        method = kwargs.get("method", "GET").upper()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                data = kwargs.get("data", {})
                response = await client.post(url, json=data, headers=headers)
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": None if response.status_code == 200 else response.text
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint path"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET"
                },
                "data": {
                    "type": "object",
                    "description": "Request payload for POST/PUT"
                }
            },
            "required": ["endpoint"]
        }
```

#### 3. Package Installation and Configuration

Once your package is ready, install it in your MCP server environment:

```bash
# Install from local development
pip install -e ./my-mcp-tools

# Or install from PyPI
pip install my-custom-mcp-tools

# Or install from Git repository
pip install git+https://github.com/yourorg/my-mcp-tools.git
```

#### 4. Configure in MCP Server

Add your external tool to `config/tools.yaml`:

```yaml
Domains:
  - Name: CUSTOM_API
    Description: Custom API integration tools

mcp_classes:
  - Domain: CUSTOM_API
    class_type: my_mcp_tools.tools.custom_api.CustomAPITool
    class_name: custom_api_tool
    class_description: Custom API integration tool
    class_initialization_params:
      params:
        api_key: "${CUSTOM_API_KEY}"
        base_url: "https://api.example.com"
    tools:
      - function: execute
        function_description: Execute custom API calls
        tool_parameters:
          - name: endpoint
            description: API endpoint to call
            allowed_values: string
          - name: method
            description: HTTP method
            allowed_values: ["GET", "POST", "PUT", "DELETE"]
          - name: data
            description: Request payload
            allowed_values: object
```

### Dynamic Loading Process

The MCP Server uses dynamic imports to load external packages:

1. **Configuration Parsing**: Server reads `class_type` from configuration
2. **Dynamic Import**: Uses `importlib` to load the specified module and class
3. **Validation**: Ensures the class inherits from proper base classes
4. **Registration**: Registers the tool in the internal registry
5. **Instantiation**: Creates tool instances with provided configuration
6. **Integration**: Makes tools available through MCP protocol

This process allows for complete decoupling between the server core and tool implementations.

### Best Practices for External Packages

- **Use proper base classes**: Always inherit from `Tool` or `Resource`
- **Handle errors gracefully**: Implement comprehensive error handling
- **Document thoroughly**: Include docstrings and README documentation
- **Version dependencies**: Pin dependency versions for stability
- **Test extensively**: Include unit and integration tests
- **Follow naming conventions**: Use descriptive names for classes and methods
- **Secure configuration**: Use environment variables for sensitive data

## Creating New Tools

### Quick Start

1. **Create your tool class** inheriting from the enhanced base:

```python
# my_custom_tool.py
from mcp_server.tools.enhanced_base import Tool, ToolConfig
from typing import Dict, Any

class MyCustomTool(Tool):
    """Custom tool for demonstration."""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        # Access configuration parameters
        self.api_key = config.params.get("api_key")
        self.base_url = config.params.get("base_url", "https://api.example.com")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        action = kwargs.get("action", "default")
        
        if action == "get_data":
            return await self._get_data(kwargs.get("query", ""))
        elif action == "process":
            return await self._process_data(kwargs.get("data", {}))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_data", "process"],
                    "description": "Action to perform"
                },
                "query": {
                    "type": "string",
                    "description": "Query parameter for get_data action"
                },
                "data": {
                    "type": "object",
                    "description": "Data to process"
                }
            },
            "required": ["action"],
            "additionalProperties": True
        }
    
    async def _get_data(self, query: str) -> Dict[str, Any]:
        """Private method to fetch data."""
        # Implement your API call logic here
        return {"result": f"Data for query: {query}"}
    
    async def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Private method to process data."""
        # Implement your processing logic here
        return {"processed": data, "status": "complete"}
```

2. **Add tool configuration** to your `config/tools.yaml`:

```yaml
Domains:
  - Name: CUSTOM
    Description: Custom tools domain

mcp_classes:
  - Domain: CUSTOM
    class_type: path.to.your.module.MyCustomTool
    class_name: my_custom_tool
    class_description: Custom tool for demonstration purposes
    class_initialization_params:
      params:
        api_key: "${MY_TOOL_API_KEY}"
        base_url: "https://api.example.com"
        timeout: 30
    tools:
      - function: execute
        function_description: Execute custom tool operations
        tool_parameters:
          - name: action
            description: Action to perform
            allowed_values: ["get_data", "process"]
          - name: query
            description: Query parameter for get_data
            allowed_values: string
          - name: data
            description: Data object for process
            allowed_values: object
```

3. **Set environment variables**:

```bash
# Windows
set MY_TOOL_API_KEY=your-api-key-here

# Linux/Mac
export MY_TOOL_API_KEY=your-api-key-here
```

### MCP Tool Output Schemas

Starting with version 2025-09-25, the MCP Server supports explicit output schema configuration for tools. This enhancement allows you to define structured response schemas that MCP clients can use to better understand and validate tool outputs.

#### Configuring Output Schemas

You can define explicit output schemas in your `tools.yaml` configuration using the `tool_output_schema` field:

```yaml
tools:
  - function: _current_conditions
    function_description: Get current weather conditions
    tool_parameters:
      - name: latitude
        description: Latitude in decimal degrees
        allowed_values: string
      - name: longitude
        description: Longitude in decimal degrees
        allowed_values: string
    tool_output_schema:
      title: "Weather API Response Schema"
      description: "Structured weather data response"
      type: "object"
      properties:
        status_code:
          type: "integer"
          description: "HTTP status code"
        headers:
          type: "object"
          description: "Response headers"
          additionalProperties: true
        body:
          type: "object"
          description: "Weather data payload"
          properties:
            temperature:
              type: "object"
              properties:
                degrees:
                  type: "number"
                  description: "Temperature value"
                unit:
                  type: "string"
                  enum: ["FAHRENHEIT", "CELSIUS"]
              required: ["degrees", "unit"]
            weatherCondition:
              type: "object"
              properties:
                type:
                  type: "string"
                  enum: ["CLEAR", "CLOUDY", "RAIN", "SNOW"]
                description:
                  type: "object"
                  properties:
                    text:
                      type: "string"
                      description: "Human-readable condition"
                  required: ["text"]
              required: ["type", "description"]
          required: ["temperature", "weatherCondition"]
      required: ["status_code", "headers", "body"]
```

#### Key Features

- **JSON Schema Validation**: Output schemas follow JSON Schema Draft 07 specification
- **Override Detection**: The system logs warnings when explicit schemas override implicit class-based schemas
- **Optional Configuration**: The `tool_output_schema` field is optional and doesn't affect existing functionality
- **Structured Responses**: Helps MCP clients understand and validate tool response formats

#### Schema Definition Guidelines

1. **Use descriptive titles and descriptions** for better documentation
2. **Define required fields** to ensure consistent response structure  
3. **Use enums for constrained values** to improve validation
4. **Include nested object definitions** for complex data structures
5. **Set appropriate data types** (string, number, integer, boolean, object, array)

#### Warning Messages

When an explicit output schema is defined for a tool that already has an implicit schema method (like `get_output_schema()` in the tool class), the system will log a warning:

```
WARNING: Tool google_weather.current_conditions: Explicit output schema defined in configuration overrides implicit schema from tool class method
```

This helps developers identify potential conflicts between configuration-based and code-based schema definitions.

### Advanced Tool Patterns

#### Specialized Base Classes

For tools with common functionality, create specialized base classes:

```python
from mcp_server.tools.enhanced_base import Tool, ToolConfig

class APITool(Tool):
    """Base class for API-based tools."""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.api_key = config.params.get("api_key")
        self.base_url = config.params.get("base_url", "")
        self.timeout = config.params.get("timeout", 30)
    
    async def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Common HTTP request logic."""
        import httpx
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            return {
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": None if response.status_code == 200 else response.text
            }
```

#### Multiple Function Tools

For tools with multiple functions (like GoogleWeatherTool):

```yaml
tools:
  - function: _current_data
    function_description: Get current data
    tool_parameters:
      - name: location
        description: Location parameter
        allowed_values: string
  - function: _historical_data
    function_description: Get historical data
    tool_parameters:
      - name: location
        description: Location parameter
        allowed_values: string
      - name: days
        description: Number of days
        allowed_values: number
```

#### Parameter Validation

Use Pydantic for advanced parameter validation:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class ToolParams(BaseModel):
    """Validation model for tool parameters."""
    location: str = Field(..., min_length=1, description="Location name")
    days: Optional[int] = Field(default=7, ge=1, le=30, description="Number of days")
    units: str = Field(default="metric", pattern="^(metric|imperial)$")
    
    @validator('location')
    def validate_location(cls, v):
        if not v.strip():
            raise ValueError('Location cannot be empty')
        return v.strip()

class MyValidatedTool(Tool):
    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            # Validate parameters using Pydantic
            params = ToolParams(**kwargs)
            return await self._process_validated_params(params)
        except Exception as e:
            return {"error": f"Parameter validation failed: {str(e)}"}
```

## Resources

The MCP Server supports dynamic resource configuration, allowing access to both public HTTP resources and internal MCP server resources. Resources provide a way to access external data sources and internal content through a unified interface.

### Resource Types

#### Public Resources
- **Access Type**: `public`
- **Description**: Resources accessible directly from the internet with HTTP/HTTPS URLs
- **Use Cases**: Public APIs, data files, web content
- **Example**: CSV files from GitHub, public API endpoints

#### MCP Server Resources
- **Access Type**: `mcp_server`
- **Description**: Resources where content is generated by internal MCP server functions
- **Use Cases**: Dynamic content generation, parameterized responses, business logic
- **Example**: Client-specific configurations, processed data

### Creating Resources

#### 1. Public HTTP Resource

```python
# mcp_server/resources/example1/publichttpresource.py
from mcp_server.resources.base import Resource
import httpx

class HttpResource(Resource):
    """Resource class for accessing public HTTP/HTTPS resources."""
    
    async def get_resource_content(self, resource_name: str, parameters=None) -> str:
        """Get content for a specific named resource."""
        resource_config = self._find_resource_config(resource_name)
        url = resource_config.uri
        
        # Substitute parameters if provided
        if parameters:
            url = self.substitute_parameters(url, parameters)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text
            else:
                raise ValueError(f"HTTP error {response.status_code}")
```

#### 2. MCP Server Resource

```python
# mcp_server/resources/example1/privateresourceexample.py
from mcp_server.resources.base import Resource

class ExamplePrivateResources(Resource):
    """Resource class for internal MCP server resources."""
    
    async def _sample_parameterized_resource(self, parameters) -> str:
        """Generate content based on client parameter."""
        client = parameters.get("client", "").lower()
        
        if client == "acme":
            return "This is the roadrunner client"
        elif client == "bigrock":
            return "We make tools to smash birds"
        else:
            return f"Unknown client: {client}"
```

### Configuration

Resources are configured in the `tools.yaml` file alongside tools. Each resource class can manage multiple resources.

#### Basic Resource Configuration

```yaml
Domains:
  - Name: USECASEY
    Description: Example resource domain

mcp_classes:
  # Public HTTP Resource Class
  - Domain: USECASEY
    class_type: mcp_server.resources.example1.publichttpresource.HttpResource
    class_name: http_resources
    class_description: Public example resource types.
    class_initialization_params:
      params:
    tools:
    resources:
      - name: weather_data
        description: Static weather data from GitHub.
        type: csv
        access: public
        uri: https://raw.githubusercontent.com/velicki/Weather_Data_Analysis_Project/refs/heads/main/Weather_Data.csv

  # Private MCP Server Resource Class  
  - Domain: USECASEY
    class_type: mcp_server.resources.example1.privateresourceexample.ExamplePrivateResources
    class_name: example_private_resources
    class_description: Example private resource types.
    class_initialization_params:
      params:
    tools:
    resources:
      - name: sample_parameterized_resource
        description: Sample parameterized resource with client-specific responses.
        function: _sample_parameterized_resource
        type: txt
        access: mcp_server
        uri: //sampledata/{client}/
        resource_parameters:
          - name: client
            description: Client ID for personalized content.
            allowed_values: string
```

### Resource Parameters

Resources support parameterization through URI templates and parameter definitions:

#### Parameter Substitution
- Use `{parameter_name}` in URIs for parameter substitution
- Parameters are defined in the `resource_parameters` section
- The system automatically substitutes parameter values in URIs

#### Parameter Configuration

```yaml
resource_parameters:
  - name: client
    description: Client identifier
    allowed_values: string
  - name: format
    description: Output format
    allowed_values: [json, xml, csv]
  - name: limit
    description: Maximum number of results
    allowed_values: number
```

### Resource Architecture

```
mcp_server/
├── resources/                # Resource implementations
│   ├── base.py              # Abstract base classes and configuration
│   ├── registry.py          # Resource registration system
│   └── example1/            # Example resource implementations
│       ├── publichttpresource.py    # Public HTTP resources
│       └── privateresourceexample.py # Private MCP resources
```

#### Key Components

##### Resource Base Classes (`resources/base.py`)
- **ResourceConfig**: Pydantic model for resource configuration
- **ResourceParameter**: Parameter definition and validation
- **Resource**: Abstract base class for all resources
- **ResourceAccessType**: Enum for access types (public, mcp_server)

##### Resource Registry (`resources/registry.py`)
- **ResourceRegistry**: Manages resource class registration and instances
- **Dynamic loading**: Import resource classes from configuration
- **Error handling**: Comprehensive error reporting for resource issues

### Usage Examples

#### Fetching Public Resource Content

```python
from mcp_server.resources.example1.publichttpresource import HttpResource

# Configure resource
config = {
    "name": "http_resources",
    "params": {
        "resources": [
            {
                "name": "weather_data",
                "type": "csv",
                "access": "public",
                "uri": "https://example.com/weather.csv"
            }
        ]
    }
}

# Create and use resource
resource = HttpResource(config)
content = await resource.get_resource_content("weather_data")
```

#### Using Parameterized Resources

```python
from mcp_server.resources.example1.privateresourceexample import ExamplePrivateResources

# Configure parameterized resource
config = {
    "name": "private_resources",
    "params": {
        "resources": [
            {
                "name": "client_config",
                "function": "_sample_parameterized_resource",
                "type": "txt",
                "access": "mcp_server",
                "uri": "//config/{client}/",
                "resource_parameters": [
                    {"name": "client", "description": "Client ID", "allowed_values": "string"}
                ]
            }
        ]
    }
}

# Use with parameters
resource = ExamplePrivateResources(config)
content = await resource.get_resource_content("client_config", {"client": "acme"})
# Returns: "This is the roadrunner client"
```

### Testing Resources

Use the provided test script to verify resource functionality:

```bash
python test_resources.py
```

The test script validates:
- Public HTTP resource fetching
- Parameterized MCP server resources
- Configuration loading and parsing
- Parameter substitution and validation

### Advanced Resource Patterns

#### Multi-Resource Classes
A single resource class can manage multiple related resources:

```yaml
resources:
  - name: current_data
    description: Current data endpoint
    type: json
    access: public
    uri: https://api.example.com/current
  - name: historical_data
    description: Historical data with date range
    type: json
    access: public
    uri: https://api.example.com/history/{start_date}/{end_date}
    resource_parameters:
      - name: start_date
        description: Start date (YYYY-MM-DD)
        allowed_values: string
      - name: end_date
        description: End date (YYYY-MM-DD)
        allowed_values: string
```

#### Environment-Based Configuration

```yaml
class_initialization_params:
  params:
    api_key: "${EXTERNAL_API_KEY}"
    base_url: "${EXTERNAL_API_URL}"
```

#### Custom Resource Types

Extend the base Resource class for specialized functionality:

```python
from mcp_server.resources.base import Resource
import json

class JsonApiResource(Resource):
    """Specialized resource for JSON APIs."""
    
    async def get_content(self, parameters=None):
        content = await super().get_content(parameters)
        # Parse and validate JSON
        try:
            data = json.loads(content)
            return self._process_json_data(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response")
    
    def _process_json_data(self, data):
        """Override to add custom JSON processing."""
        return json.dumps(data, indent=2)
```

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip or conda package manager

### Method 1: Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows
.\.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Conda Environment

```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate environment
conda activate MCPServer
```

### Environment Variables

Set required environment variables for your tools:

```bash
# Required for Google Weather Tool
set GOOGLE_WEATHER_API_KEY=your-weather-api-key
set GOOGLE_MAPS_API_KEY=your-maps-api-key

# Required for Plaid Tool
set PLAID_CLIENT_ID=your-plaid-client-id
set PLAID_SECRET=your-plaid-secret

# Optional: Custom config path
set CONFIG_PATH=config/tools.secure.yaml
```

## Usage

### Running the Server

#### Development Mode

```bash
# Using new modular architecture (recommended)
python -m mcp_server.server.app

# Using legacy interface (deprecated, shows warnings)
python -m mcp_server
```

#### Production Mode

```bash
# Set production environment
set LOG_LEVEL=info
set HOST=0.0.0.0
set HEALTH_PORT=8080

# Run server
python -m mcp_server.server.app
```

### Configuration

#### Secure Configuration (Recommended)

Use `config/tools.secure.yaml` with environment variables:

```yaml
# config/tools.secure.yaml
Domains:
  - Name: WEATHER
    Description: Weather and geocoding tools

mcp_classes:
  - Domain: WEATHER
    class_type: mcp_server.tools.weather.google_weather.GoogleWeatherTool
    class_name: google_weather
    class_description: Google Weather API tools
    class_initialization_params:
      params:
        api_key: "${GOOGLE_WEATHER_API_KEY}"
        geocoding_api_key: "${GOOGLE_MAPS_API_KEY}"
        base_url: https://weather.googleapis.com/v1
```

#### Legacy Configuration

The server maintains backward compatibility with the original format:

```yaml
# config/tools.yaml (legacy format)
Domains:
  - Name: WEATHER
    Description: Weather tools

mcp_classes:
  - Domain: WEATHER
    class_type: mcp_server.tools.weather.google_weather.GoogleWeatherTool
    # ... configuration continues
```

### Health Endpoints

The server provides health check endpoints:

- **Liveness**: `GET /healthz` - Returns `{"ok": true, "status": "healthy"}`
- **Readiness**: `GET /readyz` - Returns `{"ok": true, "status": "ready"}`
- **MCP Mounts**: `GET /mcp` - Lists all mounted MCP endpoints

```bash
# Check server health
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/mcp
```

## Docker Deployment

### Building the Image

```bash
docker build -t mcp-server:latest .
```

### Running with Docker

```bash
# Run with environment variables
docker run -d \
  --name mcp-server \
  -p 8080:8080 \
  -e GOOGLE_WEATHER_API_KEY=your-key \
  -e GOOGLE_MAPS_API_KEY=your-key \
  -e CONFIG_PATH=/app/config/tools.secure.yaml \
  mcp-server:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  mcp-server:
    build: ..
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_WEATHER_API_KEY=${GOOGLE_WEATHER_API_KEY}
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
      - CONFIG_PATH=/app/config/tools.yaml
    volumes:
      - ./config:/app/config:ro
```

## Kubernetes Deployment

Deploy using the provided Kubernetes manifest:

```bash
# Apply deployment
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods -l app=mcp-server
kubectl get services mcp-server

# View logs
kubectl logs -f deployment/mcp-server
```

## API Documentation

### MCP Protocol Endpoints

Each domain is mounted under `/mcp/{domain-slug}`:

- **Weather Tools**: `/mcp/weather`
- **Financial Tools**: `/mcp/financial` (if Plaid is configured)
- **Custom Domains**: `/mcp/{your-domain-slug}`

### Tool Invocation

Tools are invoked through the MCP protocol with the following pattern:

```json
{
  "method": "tools/call",
  "params": {
    "name": "google_weather.current_conditions",
    "arguments": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "unitsSystem": "imperial"
    }
  }
}
```

### Available Tools

#### Google Weather Tool

**Functions:**
- `current_conditions` - Get current weather conditions
- `hourly_forecast` - Get hourly forecast (up to 48 hours)
- `daily_forecast` - Get daily forecast (up to 10 days)
- `geocode` - Convert address to coordinates

**Example Usage:**
```json
{
  "name": "google_weather.current_conditions",
  "arguments": {
    "location": "Seattle, WA"
  }
}
```

#### Plaid Tool

**Functions:**
- `create_link_token` - Create link token for Plaid Link
- `exchange_public_token` - Exchange public token for access token
- `get_accounts` - Get account information
- `get_balances` - Get account balances
- `get_transactions` - Get transaction history

## Development

### Project Structure

```
├── mcp_server/              # Main package
├── config/                  # Configuration files
├── tests/                   # Test suite
├── scripts/                # Development scripts
├── k8s/                    # Kubernetes manifests
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project configuration
└── Dockerfile             # Container definition
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio coverage

# Run tests
python -m pytest tests/ -v

# Run with coverage
coverage run -m pytest tests/
coverage report -m
coverage html  # Generate HTML report
```

### Code Quality

The project follows Python best practices:

- **Type hints**: Full typing with mypy support
- **Pydantic validation**: Runtime type checking and validation
- **Error handling**: Comprehensive exception hierarchy
- **Documentation**: Docstrings for all public methods
- **Security**: Environment-based secrets management

### Adding New Domains

1. **Define domain** in configuration:
```yaml
Domains:
  - Name: MY_DOMAIN
    Description: Custom domain for my tools
```

2. **Create tools** for the domain:
```python
# my_domain_tool.py
class MyDomainTool(Tool):
    # Implementation here
    pass
```

3. **Register in configuration**:
```yaml
mcp_classes:
  - Domain: MY_DOMAIN
    class_type: path.to.my_domain_tool.MyDomainTool
    # ... configuration
```

## Migration from Legacy Architecture

If upgrading from the original monolithic version:

### Automatic Migration

The server provides backward compatibility:
- Old configuration formats are automatically converted
- Legacy imports show deprecation warnings
- All original functionality is preserved

### Manual Migration (Recommended)

1. **Update imports**:
```python
# Old
from mcp_server.app import run

# New
from mcp_server.server.app import run
```

2. **Use secure configuration**:
```yaml
# Move from config/tools.yaml to config/tools.secure.yaml
# Replace hardcoded API keys with environment variables
api_key: "${GOOGLE_WEATHER_API_KEY}"
```

3. **Update tool class paths**:
```yaml
# Old
class_type: mcp_server.tools.google_weather.GoogleWeatherTool

# New
class_type: mcp_server.tools.weather.google_weather.GoogleWeatherTool
```

## Troubleshooting

### Common Issues

**Tool Loading Failures**
- Verify `class_type` paths are correct
- Check that all required environment variables are set
- Ensure tool classes inherit from proper base classes

**Configuration Errors**
- Validate YAML syntax
- Check environment variable names and values
- Verify file paths and permissions

**API Connection Issues**
- Confirm API keys are valid and properly set
- Check network connectivity and firewall settings
- Review rate limits and quotas

**Health Check Failures**
- Verify server is running on expected port
- Check for port conflicts
- Review server logs for startup errors

### Logging

Enable detailed logging for debugging:

```bash
set LOG_LEVEL=debug
python -m mcp_server.server.app
```

### Getting Help

1. **Check the logs** for detailed error messages
2. **Verify configuration** against examples in this README
3. **Test with curl** to isolate issues
4. **Review the source code** - it's well-documented!

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd MCPServer

# Setup development environment
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Install pre-commit hooks (if available)
pre-commit install

# Run tests
python -m pytest tests/
```

## License

[Add your license information here]

## Changelog

### v2.0.0 (September 24, 2025)
- **Major Architecture Refactoring**: Complete modular redesign
- **Security Enhancements**: Environment-based configuration
- **Enhanced Tool Framework**: Improved base classes and type safety
- **Backward Compatibility**: Legacy support with deprecation warnings
- **Documentation**: Comprehensive README and code documentation

### v1.0.0 (Previous)
- Initial monolithic implementation
- Basic tool support
- Configuration via YAML files
