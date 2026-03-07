"""
Oracle MCP Server for ATLAS.

Main MCP server implementation that exposes ATLAS functionality
to AI assistants via Model Context Protocol.

Usage:
    # As stdio server (for Claude Code)
    python -m atlas.mcp.server

    # Or programmatically
    from atlas.mcp import get_oracle_server
    server = get_oracle_server()
    await server.run_stdio()
"""

import asyncio
import json
import logging
import sys
from typing import Any, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        Resource,
        TextContent,
        EmbeddedResource,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None

from .models import OracleConfig, ToolCallResult
from .tools import get_tool_definitions, ToolExecutor
from .resources import get_resource_definitions, ResourceProvider

logger = logging.getLogger(__name__)

# Singleton instance
_oracle_server: Optional["OracleMCPServer"] = None


def get_oracle_server(
    project_manager=None,
    agent_manager=None,
    knowledge_manager=None,
    memory_manager=None,
    config: Optional[OracleConfig] = None,
) -> "OracleMCPServer":
    """Get or create the global Oracle MCP Server instance.

    Args:
        project_manager: ATLAS ProjectManager instance
        agent_manager: ATLAS AgentManager instance
        knowledge_manager: ATLAS KnowledgeManager instance
        memory_manager: ATLAS MemoryManager instance
        config: Server configuration

    Returns:
        OracleMCPServer instance
    """
    global _oracle_server
    if _oracle_server is None:
        _oracle_server = OracleMCPServer(
            project_manager=project_manager,
            agent_manager=agent_manager,
            knowledge_manager=knowledge_manager,
            memory_manager=memory_manager,
            config=config,
        )
    return _oracle_server


class OracleMCPServer:
    """MCP Server exposing ATLAS to AI assistants.

    Provides tools and resources for:
    - Project and task management
    - Task execution through agent pipeline
    - Knowledge base search
    - Memory context retrieval
    - Agent status monitoring
    """

    def __init__(
        self,
        project_manager=None,
        agent_manager=None,
        knowledge_manager=None,
        memory_manager=None,
        config: Optional[OracleConfig] = None,
    ):
        """Initialize the Oracle MCP Server.

        Args:
            project_manager: ATLAS ProjectManager instance
            agent_manager: ATLAS AgentManager instance
            knowledge_manager: ATLAS KnowledgeManager instance
            memory_manager: ATLAS MemoryManager instance
            config: Server configuration
        """
        self.config = config or OracleConfig.from_env()
        self.project_manager = project_manager
        self.agent_manager = agent_manager
        self.knowledge_manager = knowledge_manager
        self.memory_manager = memory_manager

        # Initialize tool executor and resource provider
        self.tool_executor = ToolExecutor(
            project_manager=project_manager,
            agent_manager=agent_manager,
            knowledge_manager=knowledge_manager,
            memory_manager=memory_manager,
        )
        self.resource_provider = ResourceProvider(
            project_manager=project_manager,
            agent_manager=agent_manager,
            memory_manager=memory_manager,
        )

        # Get definitions
        self.tool_definitions = get_tool_definitions()
        self.resource_definitions = get_resource_definitions()

        # Create MCP server if available
        self._server: Optional[Server] = None
        if MCP_AVAILABLE:
            self._server = Server("atlas-oracle")
            self._register_handlers()
        else:
            logger.warning("MCP library not available. Install with: pip install mcp>=0.9.0")

    def _register_handlers(self):
        """Register MCP handlers for tools and resources."""
        if not self._server:
            return

        @self._server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name=td.name,
                    description=td.description,
                    inputSchema=td.input_schema,
                )
                for td in self.tool_definitions
            ]

        @self._server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool call."""
            logger.info(f"Tool call: {name} with args: {arguments}")

            # Check if tool execution is allowed
            if name == "execute_task" and not self.config.allow_task_execution:
                return [TextContent(
                    type="text",
                    text="Error: Task execution is disabled in server configuration",
                )]

            if name in ["create_task"] and not self.config.allow_project_modification:
                return [TextContent(
                    type="text",
                    text="Error: Project modification is disabled in server configuration",
                )]

            # Execute tool
            result = await self.tool_executor.execute(name, arguments or {})

            # Convert to MCP response format
            mcp_response = result.to_mcp_response()
            return [TextContent(type="text", text=item["text"]) for item in mcp_response]

        @self._server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri=rd.uri,
                    name=rd.name,
                    description=rd.description,
                    mimeType=rd.mime_type,
                )
                for rd in self.resource_definitions
            ]

        @self._server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content."""
            logger.info(f"Resource read: {uri}")

            content = await self.resource_provider.get_resource(uri)
            if content is None:
                return json.dumps({"error": f"Resource not found: {uri}"})

            # Return the text content
            return content.to_mcp_response()["text"]

    def update_managers(
        self,
        project_manager=None,
        agent_manager=None,
        knowledge_manager=None,
        memory_manager=None,
    ):
        """Update manager references (for late binding).

        Args:
            project_manager: ATLAS ProjectManager instance
            agent_manager: ATLAS AgentManager instance
            knowledge_manager: ATLAS KnowledgeManager instance
            memory_manager: ATLAS MemoryManager instance
        """
        if project_manager is not None:
            self.project_manager = project_manager
            self.tool_executor.project_manager = project_manager
            self.resource_provider.project_manager = project_manager

        if agent_manager is not None:
            self.agent_manager = agent_manager
            self.tool_executor.agent_manager = agent_manager
            self.resource_provider.agent_manager = agent_manager

        if knowledge_manager is not None:
            self.knowledge_manager = knowledge_manager
            self.tool_executor.knowledge_manager = knowledge_manager

        if memory_manager is not None:
            self.memory_manager = memory_manager
            self.tool_executor.memory_manager = memory_manager
            self.resource_provider.memory_manager = memory_manager

    async def run_stdio(self):
        """Run the MCP server using stdio transport.

        This is the main entry point for CLI usage with Claude Code.
        """
        if not MCP_AVAILABLE:
            logger.error("MCP library not available. Install with: pip install mcp>=0.9.0")
            sys.exit(1)

        if not self._server:
            logger.error("MCP server not initialized")
            sys.exit(1)

        logger.info("Starting ATLAS Oracle MCP Server (stdio mode)")

        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options(),
            )

    def get_server(self) -> Optional[Server]:
        """Get the underlying MCP Server instance."""
        return self._server


async def main():
    """Main entry point for CLI usage."""
    # Configure logging to stderr (stdout is for MCP communication)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    # Try to load ATLAS managers
    project_manager = None
    agent_manager = None

    try:
        from pathlib import Path
        from atlas.projects.manager import ProjectManager

        data_dir = Path(__file__).parent.parent.parent / "data"
        project_manager = ProjectManager(data_dir)
        await project_manager.init_db()
        logger.info("Loaded ProjectManager")
    except Exception as e:
        logger.warning(f"Could not load ProjectManager: {e}")

    try:
        from atlas.agents.manager import AgentManager
        # AgentManager requires router and memory, try to create minimal version
        # For now, we'll leave it None and let tools fail gracefully
        pass
    except Exception as e:
        logger.warning(f"Could not load AgentManager: {e}")

    # Create and run server
    server = get_oracle_server(
        project_manager=project_manager,
        agent_manager=agent_manager,
    )

    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
