"""Detect optional SDK modules without mistaking tests/mcp for the SDK."""
from importlib.util import find_spec


def mcp_available():
    try:
        return all(find_spec(name) is not None for name in (
            "mcp.server.mcpserver", "mcp.types", "aiofiles"))
    except ModuleNotFoundError:
        # unittest discovery exposes tests/mcp as a namespace package when
        # the optional SDK is absent; that package has no server submodule.
        return False


MCP_AVAILABLE = mcp_available()
