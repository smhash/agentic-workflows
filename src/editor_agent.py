"""Editor Agent - executes editorial tasks such as reflection, critique, or revision."""

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class EditorAgent:
    """Agent responsible for editing and improving content."""
    
    def __init__(self):
        """Initialize the EditorAgent."""
        self.openai = OpenAI()
    
    async def edit(self, task: str, model: str = "gpt-4o", context: str = "") -> str:
        """
        Executes editorial tasks such as reflection, critique, or revision.
        
        Args:
            task: The editorial task to execute.
            model: Language model to use (default: "gpt-4o").
            context: Optional context from previous steps.
            
        Returns:
            str: Edited or critiqued text content.
        """
        print("==================================")
        print("🧠 Editor Agent")
        print("==================================")
        
        system_prompt = (
            "You are an editor agent. Your role is to reflect on, critique, and improve "
            "drafts by analyzing clarity, structure, coherence, and academic quality. "
            "Provide thoughtful, constructive feedback or revisions to strengthen the text."
        )
        
        # Build user message with context
        user_content = task
        if context:
            user_content = f"""Here is the context of what has been done so far:
{context}

Your task:
{task}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        print("✅ Output:\n", content)
        
        return content

