"""Research Agent - executes research tasks using MCP tools."""

import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from .utils.mcp_client import MCPClient

load_dotenv()


class ResearchAgent:
    """Agent responsible for executing research tasks using external tools via MCP."""
    
    def __init__(self, mcp_client: MCPClient = None):
        """
        Initialize the ResearchAgent.
        
        Args:
            mcp_client: MCP client instance. Must be initialized with tools available.
        """
        self.openai = OpenAI()
        self.mcp_client = mcp_client
        if mcp_client is None:
            raise ValueError("MCP client is required for ResearchAgent")
    
    def _get_tools_in_openai_format(self):
        """Get research tools in OpenAI function calling format from MCP.
        
        Raises:
            RuntimeError: If MCP client is not initialized or tools are not available.
        """
        if not self.mcp_client.available_tools:
            raise RuntimeError("MCP client tools are not available. Ensure MCP client is initialized before using ResearchAgent.")
        
        openai_tools = []
        for tool in self.mcp_client.available_tools:
            # Filter for research-related tools
            tool_name = tool["name"]
            if tool_name in ["arxiv_search", "wikipedia_search"]:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                })
        return openai_tools
    
    async def _execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool call via MCP client."""
        session = self.mcp_client.get_session_for_tool(tool_name)
        if not session:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})
        
        try:
            result = await session.call_tool(tool_name, arguments=arguments)
            
            # Convert result content to string
            if isinstance(result.content, list):
                content_str = "\n".join(
                    item.text if hasattr(item, 'text') else str(item)
                    for item in result.content
                )
            else:
                content_str = str(result.content)
            
            return content_str
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
    
    async def execute_research(self, task: str, model: str = "gpt-4o", context: str = "", topic: str = None) -> str:
        """
        Executes a research task using MCP tools.
        
        Args:
            task: The research task to execute.
            model: Language model to use (default: "gpt-4o").
            context: Optional context from previous steps.
            topic: Optional original research topic for consistent document storage.
            
        Returns:
            str: Research summary text.
        """
        print("==================================")
        print("🔍 Research Agent")
        print("==================================")
        
        current_time = datetime.now().strftime('%Y-%m-%d')
        
        system_prompt = (
            "You are a research assistant specialized in gathering and synthesizing information from external sources. "
            "Your role is to use available tools to search for information and compile findings into clear, comprehensive research summaries. "
            "Use tools when helpful and always synthesize the information into a coherent summary."
        )
        
        # Build user message with context
        # Truncate context to avoid token limit issues
        MAX_CONTEXT_LENGTH = 3000  # ~750 tokens for context
        if context and len(context) > MAX_CONTEXT_LENGTH:
            context = context[:MAX_CONTEXT_LENGTH] + f"\n\n[Context truncated - showing first {MAX_CONTEXT_LENGTH:,} characters of {len(context):,} total]"
        context_section = f"\n\nContext from previous steps:\n{context}" if context else ""
        
        user_prompt = f"""Today is {current_time}.

Available tools:
- arxiv_search: find academic papers from arXiv
- wikipedia_search: access encyclopedic knowledge

Your task:
{task}{context_section}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get tools in OpenAI format from MCP
        tools = self._get_tools_in_openai_format()
        
        max_turns = 6
        turn_count = 0
        
        while turn_count < max_turns:
            response = self.openai.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            turn_count += 1
            
            # Add assistant message
            assistant_msg = {
                "role": "assistant",
                "content": message.content,
            }
            
            # Check for tool calls
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
                messages.append(assistant_msg)
                
                # Process each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # For search tools, add topic parameter to ensure consistent storage
                    # This ensures all documents for a topic are stored in the same folder
                    if tool_name in ["arxiv_search", "wikipedia_search"] and topic:
                        tool_args["topic"] = topic
                    
                    # Execute tool via MCP
                    tool_result = await self._execute_tool_call(tool_name, tool_args)
                    
                    # Truncate tool results to avoid token limit issues
                    # Tool results can be very large (e.g., full PDF text), so we limit them
                    MAX_TOOL_RESULT_LENGTH = 10000  # ~2500 tokens per tool result
                    if len(tool_result) > MAX_TOOL_RESULT_LENGTH:
                        tool_result = tool_result[:MAX_TOOL_RESULT_LENGTH] + f"\n\n[Tool result truncated - showing first {MAX_TOOL_RESULT_LENGTH:,} characters of {len(tool_result):,} total]"
                    
                    # Add tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
            else:
                # No tool calls, we're done
                messages.append(assistant_msg)
                break
        
        content = messages[-1]["content"] or "No content generated."
        print("✅ Output:\n", content)
        
        return content

