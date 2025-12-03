"""Chat Interface - handles user interaction and command parsing."""

import json
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .research_orchestrator_agent import ResearchOrchestratorAgent


class ChatInterface:
    """Handles user interaction, command parsing, and input/output for the multi-agent workflow."""
    
    # Exit commands
    EXIT_COMMANDS = ('quit', 'exit')
    
    def __init__(self, orchestrator: "ResearchOrchestratorAgent") -> None:
        """
        Initialize with a ResearchOrchestratorAgent instance.
        
        Args:
            orchestrator: ResearchOrchestratorAgent instance for orchestrating multi-agent workflows.
        """
        self.orchestrator = orchestrator
    
    async def start(self) -> None:
        """
        Start the interactive chat loop.
        
        Handles user input, command parsing, and research workflow execution.
        Supports regular topics, resource commands (@topics, @<topic>), and exit commands.
        """
        print("\n" + "="*60)
        print("🔬 Multi-Agent Research Workflow")
        print("="*60)
        print("\nCommands:")
        print("  • Type a research topic to start a research workflow")
        print("  • @topics - List available research topics")
        print("  • @<topic> - View research for a specific topic")
        print("  • quit/exit - Exit the application")
        print("\n" + "="*60)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
        
                if user_input.lower() in self.EXIT_COMMANDS:
                    break
                
                # Check for @resource syntax first
                if user_input.startswith('@'):
                    await self._handle_resource_command(user_input)
                    continue
                
                # Regular topic - execute multi-agent research workflow
                await self._execute_research_workflow(user_input)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                traceback.print_exc()
    
    async def _execute_research_workflow(self, topic: str) -> None:
        """
        Execute multi-agent research workflow for a research topic.
        
        Args:
            topic: The research topic to investigate.
        """
        try:
            print(f"\n🚀 Starting research workflow for: {topic}")
            print("="*60)
            
            # Execute research workflow (uses orchestrator's model_config)
            history = await self.orchestrator.orchestrate_research_workflow(
                topic=topic,
                limit_steps=False,
                max_steps=10
            )
            
            # Display full execution history
            print("\n" + "="*60)
            print("📊 Research Workflow Execution History")
            print("="*60)
            
            for i, (step, agent_name, output) in enumerate(history, 1):
                print(f"\n--- Step {i}: {agent_name} ---")
                print(f"Task: {step}")
                print(f"Output:\n{output}")
                print("-" * 60)
            
            # Display final summary
            if history:
                print("\n" + "="*60)
                print("✅ Research Workflow Complete!")
                print("="*60)
                print(f"Total steps executed: {len(history)}")
                final_output = history[-1][-1]
                print(f"\n📄 Final Output:\n{final_output}")
            
        except Exception as e:
            print(f"\n❌ Research workflow execution failed: {str(e)}")
            raise
    
    async def _handle_resource_command(self, topic: str) -> None:
        """
        Handle @resource commands like @topics or @<topic>.
        
        Args:
            topic: The resource command (e.g., "@topics" or "@machine_learning").
        """
        # Remove @ sign  
        topic_name = topic[1:]
        if topic_name == "topics":
            resource_uri = "research://topics"
        else:
            resource_uri = f"research://{topic_name}"
        
        # Access MCP client through orchestrator
        session = self.orchestrator.mcp_client.get_session_for_resource(resource_uri)
        
        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return
        
        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\n📚 Resource: {resource_uri}")
                content_text = result.contents[0].text
                
                # Format topics resource as readable list
                if resource_uri == "research://topics":
                    try:
                        topics_data = json.loads(content_text)
                        topics = topics_data.get("topics", [])
                        if topics:
                            print("\nAvailable Topics:")
                            for topic in topics:
                                print(f"  • {topic['name']} ({topic['paper_count']} papers)")
                            print(f"\nUse @{topics[0]['name']} to access papers in that topic.")
                        else:
                            print("No topics found.")
                    except json.JSONDecodeError:
                        # Fallback to raw text if JSON parsing fails
                        print("Content:")
                        print(content_text)
                else:
                    # For other resources, display as-is
                    print("Content:")
                    print(content_text)
            else:
                print("No content available.")
        except Exception as e:
            print(f"Error accessing resource: {e}")

