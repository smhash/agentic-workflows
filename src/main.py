"""Main application entry point for multi-agent research workflow."""

import asyncio
import sys
import traceback
from typing import Optional

from dotenv import load_dotenv

from .chat_interface import ChatInterface
from .research_orchestrator_agent import ResearchOrchestratorAgent
from .utils.mcp_client import MCPClient
from .utils.model_config import ModelConfig

load_dotenv()


async def run() -> None:
    """
    Run the multi-agent research workflow application.
    
    Initializes MCP client, creates research orchestrator, and starts
    the interactive chat interface. Handles cleanup on exit.
    """
    mcp_client: Optional[MCPClient] = None
    orchestrator: Optional[ResearchOrchestratorAgent] = None
    
    try:
        # Initialize MCP client
        print("🔌 Initializing MCP client...")
        mcp_client = MCPClient()
        await mcp_client.connect_to_servers()
        print("✅ MCP client initialized\n")
        
        # Create model configuration (loads from env or uses defaults)
        model_config = ModelConfig.from_env()
        
        # Create ResearchOrchestratorAgent with initialized MCP client
        orchestrator = ResearchOrchestratorAgent(
            mcp_client=mcp_client,
            model_config=model_config
        )
        
        # Create ChatInterface and start interactive loop
        chat = ChatInterface(orchestrator)
        await chat.start()
        
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup resources
        if orchestrator:
            await orchestrator.cleanup()
        print("\n👋 Goodbye!")


def main() -> None:
    """
    Synchronous entry point for CLI.
    
    Wraps the async run() function for command-line execution.
    """
    asyncio.run(run())


if __name__ == "__main__":
    main()

