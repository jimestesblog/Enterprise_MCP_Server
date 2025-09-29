from setuptools import setup, find_packages

setup(
    name="mcp-example-resources",
    version="0.1.0",
    description="Example resource implementations for MCP Server - HTTP and private resources",
    long_description=open("docs/README.md").read(),
    long_description_content_type="text/markdown",
    author="MCP Server Team",
    author_email="contact@example.com",
    url="https://github.com/example/mcp-example-resources",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "httpx>=0.24.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    license="MIT",
)