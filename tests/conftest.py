"""Pytest fixtures for test suite."""

import pytest
from src.utils.mcp_client import MCPClient
from src.utils.model_config import ModelConfig
from src.research_orchestrator_agent import ResearchOrchestratorAgent


@pytest.fixture
async def mcp_client():
    """Create and initialize an MCP client for testing."""
    client = MCPClient()
    try:
        await client.connect_to_servers()
        yield client
    finally:
        await client.cleanup()


@pytest.fixture
async def orchestrator(mcp_client):
    """Create a ResearchOrchestratorAgent for testing with test model config."""
    model_config = ModelConfig.for_testing()
    orchestrator = ResearchOrchestratorAgent(
        mcp_client=mcp_client,
        model_config=model_config
    )
    yield orchestrator
    await orchestrator.cleanup()

