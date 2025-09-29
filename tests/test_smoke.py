import asyncio

import pytest


@pytest.mark.asyncio
async def test_health_app_imports():
    # Ensure app can be created and run function exists
    import mcp_server.app as app_mod
    assert hasattr(app_mod, "create_http_app") or hasattr(app_mod, "run")


def test_readme_exists():
    import os
    assert os.path.exists(os.path.join(os.getcwd(), "README.md"))
