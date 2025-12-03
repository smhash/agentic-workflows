"""Tests for ChatInterface."""

import os
import pytest
from unittest.mock import patch
from src.chat_interface import ChatInterface


@pytest.mark.asyncio
async def test_chat_interface_initialization(orchestrator):
    """Test ChatInterface can be initialized."""
    chat = ChatInterface(orchestrator)
    assert chat is not None
    assert chat.orchestrator == orchestrator


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_api_key_here",
    reason="OPENAI_API_KEY not set"
)
async def test_chat_interface_research_workflow_execution(orchestrator):
    """Test ChatInterface research workflow execution with mock input."""
    chat = ChatInterface(orchestrator)
    
    test_inputs = ["neural networks", "quit"]
    input_index = [0]
    
    def mock_input(prompt):
        if input_index[0] < len(test_inputs):
            result = test_inputs[input_index[0]]
            input_index[0] += 1
            return result
        return "quit"
    
    with patch('builtins.input', side_effect=mock_input):
        try:
            await chat.start()
        except SystemExit:
            pass  # Expected when 'quit' is called

