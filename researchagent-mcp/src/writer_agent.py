"""Writer Agent - executes writing tasks like drafting, expanding, or summarizing text."""

from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from .utils.mcp_client import MCPClient

load_dotenv()


class WriterAgent:
    """Agent responsible for writing and drafting content."""
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Initialize the WriterAgent.
        
        Args:
            mcp_client: Optional MCP client for accessing stored documents via resources.
        """
        self.openai = OpenAI()
        self.mcp_client = mcp_client
    
    async def write(self, task: str, model: str = "gpt-4o", context: str = "", topic: Optional[str] = None) -> str:
        """
        Executes writing tasks, such as drafting, expanding, or summarizing text.
        
        Args:
            task: The writing task to execute.
            model: Language model to use (default: "gpt-4o").
            context: Optional context from previous steps.
            topic: Optional research topic to retrieve stored documents for synthesis.
            
        Returns:
            str: Generated text content.
        """
        print("==================================")
        print("✍️ Writer Agent")
        print("==================================")
        
        # Retrieve stored documents if topic and MCP client are available
        stored_docs = ""
        if topic and self.mcp_client:
            try:
                # Normalize topic to match how documents are stored (lowercase, underscores)
                normalized_topic = topic.lower().replace(' ', '_')
                resource_uri = f"research://{normalized_topic}"
                session = self.mcp_client.get_session_for_resource(resource_uri)
                if session:
                    result = await session.read_resource(uri=resource_uri)
                    if result and result.contents:
                        stored_docs = result.contents[0].text
                        # Count documents mentioned in the retrieved content
                        doc_count = stored_docs.count("## ")  # Each document starts with ##
                        print(f"📚 Retrieved {len(stored_docs)} characters of stored documents ({doc_count} documents)")
                    else:
                        print(f"⚠️ No documents found for topic: {normalized_topic}")
                else:
                    print(f"⚠️ No MCP session found for resource: {resource_uri}")
            except Exception as e:
                print(f"⚠️ Could not retrieve stored documents: {e}")
        
        system_prompt = (
            "You are a writing agent specialized in producing clear, well-structured "
            "academic and technical content. Your job is to draft, expand, refine, or "
            "summarize text according to the user's task. "
            "When synthesizing research, you MUST use ALL available information from the stored documents. "
            "Read through every document provided and incorporate relevant information from each one. "
            "Do not skip any documents - synthesize information from all sources to create a comprehensive report. "
            "Prioritize detailed sources (arXiv papers, Wikipedia articles) but ensure you reference all documents. "
            "Ensure your report is thorough, well-organized, and includes proper citations. "
            "Structure your report with clear sections: Introduction, Background/Methodology, "
            "Applications, Challenges, and Conclusion."
        )
        
        # Build user message with stored documents, context, and task
        # Truncate context to avoid token limit issues (max 5000 chars)
        MAX_CONTEXT_LENGTH = 5000
        if context and len(context) > MAX_CONTEXT_LENGTH:
            context = context[:MAX_CONTEXT_LENGTH] + f"\n\n[Context truncated - showing first {MAX_CONTEXT_LENGTH:,} characters of {len(context):,} total]"
        
        user_content = ""
        if stored_docs:
            user_content = f"""Stored Research Documents:
{stored_docs}

"""
        if context:
            user_content += f"""Context from previous steps:
{context}

"""
        user_content += f"Your task:\n{task}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1.0
        )
        
        content = response.choices[0].message.content
        print("✅ Output:\n", content)
        
        return content

