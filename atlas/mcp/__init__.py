"""
ATLAS MCP Server - Oracle Module.

Exposes ATLAS functionality to AI assistants via Model Context Protocol.
Allows Claude Code, Cursor, and other MCP-compatible tools to:
- Query and manage projects
- Search knowledge base
- Execute tasks through agent pipeline
- Monitor agent status

Usage:
    from atlas.mcp import get_oracle_server, OracleConfig

    # Get singleton server instance
    server = get_oracle_server()

    # Run as stdio server (for Claude Code integration)
    await server.run_stdio()

Claude Code integration (settings.json):
    "mcpServers": {
        "atlas": {
            "command": "python",
            "args": ["-m", "atlas.mcp.server"]
        }
    }
"""

from .models import (
    OracleConfig,
    ToolCallResult,
    ResourceContent,
    ToolDefinition,
    ResourceDefinition,
)
from .server import OracleMCPServer, get_oracle_server

__all__ = [
    # Main server
    "OracleMCPServer",
    "get_oracle_server",
    # Configuration
    "OracleConfig",
    # Data models
    "ToolCallResult",
    "ResourceContent",
    "ToolDefinition",
    "ResourceDefinition",
]
