"""Tests for MCP client - connection, tools, and resources."""

import pytest
from src.utils.mcp_client import MCPClient


@pytest.mark.asyncio
async def test_mcp_client_connection(mcp_client):
    """Test MCP client connection and discovery."""
    assert mcp_client is not None
    assert len(mcp_client.available_tools) > 0
    assert len(mcp_client.sessions) > 0


@pytest.mark.asyncio
async def test_mcp_client_tools(mcp_client):
    """Test tool discovery and execution."""
    # Check research tools are available
    tool_names = [t['name'] for t in mcp_client.available_tools]
    assert 'arxiv_search' in tool_names
    
    # Test tool execution
    search_tool = next((t for t in mcp_client.available_tools if t['name'] == 'arxiv_search'), None)
    if search_tool:
        session = mcp_client.sessions.get(search_tool['name'])
        if session:
            result = await session.call_tool(
                search_tool['name'],
                arguments={"topic": "machine learning", "max_results": 2}
            )
            assert result is not None


@pytest.mark.asyncio
async def test_mcp_client_resources(mcp_client):
    """Test resource access."""
    resource_uri = "research://topics"
    session = mcp_client.get_session_for_resource(resource_uri)
    
    if session:
        result = await session.read_resource(uri=resource_uri)
        assert result is not None
        if result.contents:
            assert len(result.contents) > 0



