"""Research Orchestrator Agent - orchestrates the multi-agent research workflow."""

import json
import re
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from .planner_agent import PlannerAgent
from .research_agent import ResearchAgent
from .writer_agent import WriterAgent
from .editor_agent import EditorAgent
from .utils.mcp_client import MCPClient
from .utils.model_config import ModelConfig

load_dotenv()

# Constants
RESEARCH_PAPER_DIR = Path("research_papers")


class ResearchOrchestratorAgent:
    """Orchestrates the multi-agent research workflow."""
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        model_config: Optional[ModelConfig] = None
    ):
        """
        Initialize the ResearchOrchestratorAgent.
        
        Args:
            mcp_client: Optional MCP client instance. If None, creates a new one.
            model_config: Optional model configuration. If None, uses ModelConfig.from_env().
        """
        self.openai = OpenAI()
        self.mcp_client = mcp_client if mcp_client is not None else MCPClient()
        self.model_config = model_config if model_config is not None else ModelConfig.from_env()
        
        # Initialize all agents (share MCP client with research and writer agents)
        self.planner = PlannerAgent()
        self.research_agent = ResearchAgent(self.mcp_client)
        self.writer_agent = WriterAgent(self.mcp_client)  # Give writer access to stored documents
        self.editor_agent = EditorAgent()
        
        # Agent registry
        self.agent_registry = {
            "research_agent": self.research_agent.execute_research,
            "editor_agent": self.editor_agent.edit,
            "writer_agent": self.writer_agent.write,
        }
        
        # Model mapping for each agent type
        self._agent_model_map = {
            "research_agent": lambda config: config.research,
            "writer_agent": lambda config: config.writer,
            "editor_agent": lambda config: config.editor,
        }
    
    def _clean_json_block(self, raw: str) -> str:
        """Clean the contents of a JSON block that may come wrapped with Markdown backticks."""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return raw.strip()
    
    async def _decide_agent(self, step: str) -> tuple[str, str]:
        """
        Decide which agent should handle a step and extract the clean task.
        
        Args:
            step: The step instruction.
            
        Returns:
            tuple: (agent_name, task) where agent_name is one of the registered agents.
        """
        system_prompt = (
            "You are an execution manager for a multi-agent research team. "
            "Your role is to analyze instructions and route them to the appropriate specialized agent. "
            "For each instruction, identify which agent should handle it and extract a clean, actionable task description. "
            "Always return only a valid JSON object with no explanations or markdown formatting."
        )
        
        user_prompt = f"""
        Route the following instruction to the appropriate agent.

        Available agents:
        - research_agent: Handles research tasks like searching arXiv, web, and Wikipedia
        - writer_agent: Handles writing tasks like drafting, expanding, or summarizing text
        - editor_agent: Handles editorial tasks like reflecting, critiquing, or revising drafts

        Return a JSON object with two keys:
        - "agent": one of ["research_agent", "editor_agent", "writer_agent"]
        - "task": a string with the instruction that the agent should follow

        Instruction: "{step}"
        """
        
        response = self.openai.chat.completions.create(
            model=self.model_config.router,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
        )
        
        raw_content = response.choices[0].message.content
        cleaned_json = self._clean_json_block(raw_content)
        agent_info = json.loads(cleaned_json)
        
        agent_name = agent_info["agent"]
        task = agent_info["task"]
        
        return agent_name, task
    
    async def orchestrate_research_workflow(
        self,
        topic: str,
        model_config: Optional[ModelConfig] = None,
        limit_steps: bool = False,
        max_steps: int = 10
    ) -> list[tuple]:
        """
        Orchestrate a complete research workflow for a given topic.
        
        Args:
            topic: The research topic.
            model_config: Optional model configuration. If None, uses instance model_config.
            limit_steps: Whether to limit the number of steps (default: False).
            max_steps: Maximum number of steps to execute if limit_steps is True (default: 10).
            
        Returns:
            list[tuple]: Execution history as list of (step, agent_name, output) tuples.
        """
        # Use provided config or instance config
        config = model_config if model_config is not None else self.model_config
        
        # Generate plan using planner model
        plan_steps = await self.planner.generate_plan(topic, model=config.planner)
        original_step_count = len(plan_steps)
        
        if limit_steps:
            plan_steps = plan_steps[:min(len(plan_steps), max_steps)]
            if original_step_count > max_steps:
                print(f"⚠️ Limiting execution to {max_steps} steps (plan has {original_step_count} steps)")
        
        history = []
        
        print("==================================")
        print("🎯 Research Orchestrator Agent")
        print("==================================")
        
        for i, step in enumerate(plan_steps):
            # Decide which agent should handle this step (uses router model)
            agent_name, task = await self._decide_agent(step)
            
            # Build context from previous steps
            context = "\n".join([
                f"Step {j+1} executed by {a}:\n{r}" 
                for j, (s, a, r) in enumerate(history)
            ])
            
            print(f"\n🛠️ Executing with agent: `{agent_name}` on task: {task}")
            
            # Execute with the appropriate agent using model from config
            if agent_name in self.agent_registry:
                agent_func = self.agent_registry[agent_name]
                # Select model based on agent type
                if agent_name in self._agent_model_map:
                    agent_model = self._agent_model_map[agent_name](config)
                else:
                    raise ValueError(f"Unknown agent model mapping for: {agent_name}")
                
                # Pass topic to research and writer agents
                if agent_name == "research_agent":
                    output = await agent_func(task, model=agent_model, context=context, topic=topic)
                elif agent_name == "writer_agent":
                    output = await agent_func(task, model=agent_model, context=context, topic=topic)
                else:
                    output = await agent_func(task, model=agent_model, context=context)
                history.append((step, agent_name, output))
            else:
                output = f"⚠️ Unknown agent: {agent_name}"
                history.append((step, agent_name, output))
            
            print(f"✅ Output:\n{output}")
        
        # Save final document if workflow completed successfully
        if history:
            final_output = history[-1][-1]  # Last step's output
            self._save_final_report(topic, final_output)
        
        return history
    
    def _normalize_topic(self, topic: str) -> str:
        """Normalize topic name for use in file paths."""
        return topic.lower().replace(" ", "_")
    
    def _clean_markdown_code_blocks(self, content: str) -> str:
        """
        Remove markdown code block markers from content.
        
        Args:
            content: Content that may be wrapped in markdown code blocks.
            
        Returns:
            Cleaned content without code block markers.
        """
        content = content.strip()
        # Remove opening markdown code block (```markdown, ```md, or just ```)
        if content.startswith("```"):
            # Match ``` followed by optional language identifier and newline
            content = re.sub(r"^```(?:markdown|md)?\s*\n?", "", content, flags=re.MULTILINE)
        # Remove closing markdown code block (```)
        if content.endswith("```"):
            # Match newline and closing ```
            content = re.sub(r"\n?\s*```\s*$", "", content, flags=re.MULTILINE)
        return content.strip()
    
    def _save_final_report(self, topic: str, content: str) -> None:
        """
        Save the final research report to disk.
        
        Args:
            topic: The research topic.
            content: The final report content (markdown).
        """
        try:
            # Clean markdown code blocks if present
            cleaned_content = self._clean_markdown_code_blocks(content)
            
            normalized_topic = self._normalize_topic(topic)
            topic_dir = RESEARCH_PAPER_DIR / normalized_topic
            topic_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as markdown
            report_path = topic_dir / "final_report.md"
            report_path.write_text(cleaned_content, encoding="utf-8")
            
            print(f"\n💾 Final report saved to: {report_path}")
        except Exception as e:
            print(f"⚠️ Failed to save final report: {e}")
    
    async def cleanup(self):
        """Clean up MCP connections."""
        await self.mcp_client.cleanup()

