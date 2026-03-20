"""MCP (Model Context Protocol) client implementation."""

import asyncio
import json
from typing import Any, Optional, AsyncIterator

from .base import ToolDefinition, ToolRegistry, ToolResult, ToolCategory


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""

    pass


class MCPProtocolError(MCPError):
    """Raised when MCP protocol error occurs."""

    pass


class MCPServer:
    """Represents an MCP server connection."""

    def __init__(
        self,
        name: str,
        command: list[str],
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
    ):
        """Initialize an MCP server.

        Args:
            name: The server name.
            command: The command to start the server.
            args: Optional command arguments.
            env: Optional environment variables.
        """
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._process is not None and self._process.returncode is None

    async def start(self) -> None:
        """Start the MCP server process."""
        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**dict(self.env), **dict(self.env.items())},
        )

    async def stop(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None

    async def _send_request(self, method: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Send a JSON-RPC request to the server.

        Args:
            method: The RPC method name.
            params: Optional method parameters.

        Returns:
            The JSON-RPC response.

        Raises:
            MCPConnectionError: If connection fails.
            MCPProtocolError: If protocol error occurs.
        """
        if not self.is_running:
            raise MCPConnectionError(f"MCP server '{self.name}' is not running")

        self._request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        # Send request
        request_json = json.dumps(request) + "\n"
        self._process.stdin.write(request_json.encode())
        await self._process.stdin.drain()

        # Read response
        response_line = await self._process.stdout.readline()
        if not response_line:
            raise MCPConnectionError(f"MCP server '{self.name}' closed connection")

        try:
            response = json.loads(response_line.decode())
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response: {e}") from e

        # Check for errors
        if "error" in response:
            error = response["error"]
            raise MCPProtocolError(f"MCP error: {error.get('message', 'Unknown error')}")

        return response.get("result", {})

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP server connection.

        Returns:
            The initialization result.
        """
        return await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "clientInfo": {
                "name": "open-javis",
                "version": "0.1.0",
            },
        })

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Returns:
            List of tool definitions.
        """
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            name: The tool name.
            arguments: Tool arguments.

        Returns:
            The tool call result.
        """
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return result


class MCPClient:
    """Client for managing MCP server connections."""

    def __init__(self, tool_registry: ToolRegistry):
        """Initialize the MCP client.

        Args:
            tool_registry: Tool registry to register MCP tools.
        """
        self.tool_registry = tool_registry
        self._servers: dict[str, MCPServer] = {}

    async def add_server(
        self,
        name: str,
        command: list[str],
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
    ) -> None:
        """Add an MCP server.

        Args:
            name: The server name.
            command: The command to start the server.
            args: Optional command arguments.
            env: Optional environment variables.
        """
        server = MCPServer(name, command, args, env)
        await server.start()
        await server.initialize()
        self._servers[name] = server

        # Register tools from the server
        await self._register_server_tools(server)

    async def _register_server_tools(self, server: MCPServer) -> None:
        """Register tools from an MCP server.

        Args:
            server: The MCP server.
        """
        tools = await server.list_tools()

        for tool in tools:
            # Namespacing: mcp_{server}_{tool}
            tool_name = f"mcp_{server.name}_{tool['name']}"

            # Build JSON schema parameters
            parameters = tool.get("inputSchema", {})

            tool_def = ToolDefinition(
                name=tool_name,
                description=tool.get("description", ""),
                parameters=parameters,
                category=ToolCategory.MCP,
            )

            # Register with custom function that calls the MCP server
            async def mcp_tool_wrapper(arguments: dict[str, Any], _server=server, _original_name=tool["name"]):
                result = await _server.call_tool(_original_name, arguments)
                content = result.get("content", [])
                if isinstance(content, list):
                    return "\n".join(item.get("text", "") for item in content)
                return str(content)

            tool_def.function = mcp_tool_wrapper
            self.tool_registry.register(tool_def)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call an MCP tool.

        Args:
            name: The tool name.
            arguments: Tool arguments.

        Returns:
            ToolResult from execution.
        """
        # Extract server name from tool name (mcp_{server}_{tool})
        parts = name.split("_", 2)
        if len(parts) != 3 or parts[0] != "mcp":
            return ToolResult(content=f"Invalid MCP tool name: {name}", is_error=True)

        server_name = parts[1]
        original_name = parts[2]

        server = self._servers.get(server_name)
        if not server:
            return ToolResult(content=f"MCP server '{server_name}' not found", is_error=True)

        try:
            result = await server.call_tool(original_name, arguments)
            content = result.get("content", [])
            if isinstance(content, list):
                text_content = "\n".join(item.get("text", "") for item in content)
            else:
                text_content = str(content)

            return ToolResult(content=text_content)

        except Exception as e:
            return ToolResult(content=f"MCP error: {e}", is_error=True)

    async def remove_server(self, name: str) -> bool:
        """Remove an MCP server.

        Args:
            name: The server name.

        Returns:
            True if server was removed.
        """
        if name in self._servers:
            await self._servers[name].stop()
            del self._servers[name]
            # Remove associated tools
            to_remove = [t for t in self.tool_registry.list_all() if t.name.startswith(f"mcp_{name}_")]
            for tool in to_remove:
                self.tool_registry.remove(tool.name)
            return True
        return False

    async def stop_all(self) -> None:
        """Stop all MCP servers."""
        for server in list(self._servers.values()):
            await server.stop()
        self._servers.clear()

    def list_servers(self) -> list[str]:
        """List all connected MCP servers.

        Returns:
            List of server names.
        """
        return list(self._servers.keys())
