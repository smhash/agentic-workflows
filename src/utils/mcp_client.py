"""MCP Client - handles client-side connections to MCP servers, capability discovery, and session management."""

from typing import Optional, Dict, List, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json


class MCPClient:
    """MCP client that connects to servers, discovers capabilities, and manages sessions."""
    
    # Resource URI prefix for fallback matching
    RESEARCH_URI_PREFIX = "research://"
    
    def __init__(self) -> None:
        """Initialize MCP client with empty capability lists."""
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[Dict[str, Any]] = []
        self.available_resources: List[Dict[str, Any]] = []
        self.sessions: Dict[str, ClientSession] = {}
    
    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """
        Connect to a single MCP server and discover its capabilities.
        
        Args:
            server_name: Name identifier for the server.
            server_config: Server configuration dictionary.
            
        Raises:
            Exception: If connection or capability discovery fails.
        """
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            print(f"✓ Connected to {server_name}")
            
            await self._discover_capabilities(session, server_name)
                
        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")
            raise
    
    async def _discover_capabilities(self, session: ClientSession, server_name: str) -> None:
        """
        Discover tools and resources from an MCP session.
        
        Args:
            session: Initialized MCP client session.
            server_name: Server name for error messages.
        """
        # Discover tools
        try:
            response = await session.list_tools()
            for tool in response.tools:
                self.sessions[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            print(f"Error listing tools for {server_name}: {e}")
        
        # Discover resources (optional capability)
        try:
            resources_response = await session.list_resources()
            if resources_response and resources_response.resources:
                for resource in resources_response.resources:
                    resource_uri = str(resource.uri)
                    self.sessions[resource_uri] = session
                    self.available_resources.append({
                        "uri": resource_uri,
                        "name": getattr(resource, 'name', resource_uri),
                        "description": getattr(resource, 'description', ''),
                        "mimeType": getattr(resource, 'mimeType', '')
                    })
        except Exception:
            # Resources are optional - some servers don't support them
            pass
    
    async def connect_to_servers(self, config_path: str = "server_config.json") -> None:
        """
        Connect to all MCP servers defined in the config file.
        
        Args:
            config_path: Path to JSON configuration file.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file is invalid JSON.
            KeyError: If config file is missing required structure.
        """
        try:
            with open(config_path, "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
            
            self._print_connection_summary()
        except FileNotFoundError:
            print(f"Error: Config file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            raise
        except Exception as e:
            print(f"Error loading server config: {e}")
            raise
    
    def _print_connection_summary(self) -> None:
        """Print summary of discovered capabilities."""
        print("\n=== Connection Summary ===")
        print(f"Available tools: {json.dumps(self.available_tools, indent=2)}")
        print(f"Available resources: {json.dumps(self.available_resources, indent=2)}")
        print(f"Sessions: {list(self.sessions.keys())}")
        print("=" * 50)
    
    def get_session_for_tool(self, tool_name: str) -> Optional[ClientSession]:
        """
        Get the MCP session for a specific tool.
        
        Args:
            tool_name: Name of the tool.
            
        Returns:
            ClientSession if found, None otherwise.
        """
        return self.sessions.get(tool_name)
    
    def get_session_for_resource(self, resource_uri: str) -> Optional[ClientSession]:
        """
        Get the MCP session for a specific resource.
        
        Args:
            resource_uri: URI of the resource.
            
        Returns:
            ClientSession if found, None otherwise.
            
        Note:
            Falls back to any matching resource session if exact match not found
            (e.g., for research:// URIs).
        """
        session = self.sessions.get(resource_uri)
        if session:
            return session
        
        # Fallback: try to find any session with matching URI prefix
        if resource_uri.startswith(self.RESEARCH_URI_PREFIX):
            for uri, sess in self.sessions.items():
                if uri.startswith(self.RESEARCH_URI_PREFIX):
                    return sess
        
        return None
    
    async def cleanup(self) -> None:
        """Clean up all server connections."""
        await self.exit_stack.aclose()

