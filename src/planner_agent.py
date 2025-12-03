"""Planner Agent - generates step-by-step research plans for a given topic."""

import ast
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class PlannerAgent:
    """Agent responsible for creating research workflow plans."""
    
    def __init__(self):
        """Initialize the PlannerAgent."""
        self.openai = OpenAI()
    
    def _clean_code_block(self, raw: str) -> str:
        """
        Clean markdown code blocks from LLM response.
        
        Args:
            raw: Raw response string that may contain markdown code blocks.
            
        Returns:
            Cleaned string with code blocks removed.
        """
        raw = raw.strip()
        # Remove markdown code blocks (```python, ```, etc.)
        if raw.startswith("```"):
            # Remove opening ```python or ```
            raw = re.sub(r"^```(?:python|py)?\n?", "", raw)
            # Remove closing ```
            raw = re.sub(r"\n?```$", "", raw)
        return raw.strip()
    
    async def generate_plan(self, topic: str, model: str = "gpt-4o-mini") -> list[str]:
        """
        Generates a plan as a Python list of steps (strings) for a research workflow.

        Args:
            topic: Research topic to investigate.
            model: Language model to use (default: "gpt-4o-mini").

        Returns:
            List[str]: A list of executable step strings.
        """

        print("==================================")
        print("🧠 Planner Agent")
        print("==================================")

        system_prompt = (
            "You are a planning agent specialized in creating structured research workflows. "
            "Your role is to break down research topics into clear, executable step-by-step plans. "
            "Each plan must be returned as a valid Python list of strings, where each string represents "
            "an atomic, executable step. Steps should only reference capabilities of available agents and their tools. "
            "Assume tool use is available - agents can use their tools to accomplish tasks. "
            "Focus on research-related tasks like searching, summarizing, drafting, and revising. "
            "Exclude irrelevant tasks such as file management, environment setup, or data export. "
            "Return only the Python list with no additional explanation."
        )
        
        user_prompt = f"""
        Create a step-by-step research plan for the following topic.

        Available agents and their capabilities:
        - Research agent: Can search Wikipedia and arXiv for information
        - Writer agent: Can draft, expand, and summarize research content
        - Editor agent: Can reflect on, critique, and revise drafts

        Requirements:
        - Each step should be atomic and executable by one of the available agents
        - The final step should generate a Markdown document with the complete research report

        Topic: "{topic}"
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1,
        )
        
        steps_str = response.choices[0].message.content.strip()
        
        # Clean markdown code blocks if present
        steps_str = self._clean_code_block(steps_str)
        
        # Parse steps
        steps = ast.literal_eval(steps_str)
        
        # Print the generated plan
        print(f"\n📋 Generated Research Plan ({len(steps)} steps):")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        print()
        
        return steps

