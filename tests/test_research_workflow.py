"""End-to-end tests for multi-agent research workflow."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.asyncio
async def test_research_orchestrator_initialization(orchestrator):
    """Test research orchestrator can be initialized."""
    assert orchestrator is not None
    assert orchestrator.mcp_client is not None


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here",
    reason="OPENAI_API_KEY not set"
)
async def test_research_workflow_execution(orchestrator):
    """Test complete research workflow execution with limited steps."""
    history = await orchestrator.orchestrate_research_workflow(
        topic="neural networks",
        limit_steps=True,
        max_steps=3  # Keep small for testing
    )
    
    assert history is not None
    assert len(history) > 0
    
    # Verify structure
    for step, agent_name, output in history:
        assert step is not None
        assert agent_name is not None
        assert output is not None

