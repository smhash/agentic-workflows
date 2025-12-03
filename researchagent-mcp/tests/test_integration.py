#!/usr/bin/env python3
"""Integration tests for research_mcp_server.py - tests via MCP protocol with real arxiv calls."""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def test_mcp_server():
    """Test the MCP server via the protocol with real arxiv calls."""
    print("=" * 60)
    print("MCP Server Integration Tests (Real arXiv Calls)")
    print("=" * 60)
    
    # Server configuration (matches server_config.json)
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "src/research_mcp_server.py"]
    )
    
    async with AsyncExitStack() as exit_stack:
        # Connect to the server
        print("\n[1] Connecting to MCP server...")
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        
        print("    Initializing session...")
        await session.initialize()
        print("    ✓ Connected successfully!")
        
        # List available tools
        print("\n[2] Listing available tools...")
        tools = await session.list_tools()
        print(f"    ✓ Found {len(tools.tools)} tools:")
        for tool in tools.tools:
            print(f"      - {tool.name}: {tool.description[:60]}...")
        
        # List available resources
        print("\n[3] Listing available resources...")
        resources = await session.list_resources()
        print(f"    ✓ Found {len(resources.resources)} resources:")
        for resource in resources.resources:
            print(f"      - {resource.uri}")
        
        # List available prompts
        print("\n[4] Listing available prompts...")
        prompts = await session.list_prompts()
        print(f"    ✓ Found {len(prompts.prompts)} prompts:")
        for prompt in prompts.prompts:
            print(f"      - {prompt.name}: {prompt.description[:60]}...")
        
        # Test arxiv_search (REAL ARXIV CALL)
        print("\n[5] Testing arxiv_search (REAL ARXIV API CALL)...")
        print("    Searching for 'transformer architectures' with max_results=3")
        try:
            result = await session.call_tool(
                "arxiv_search",
                arguments={
                    "query": "transformer architectures",
                    "max_results": 3
                }
            )
            print(f"    ✓ Tool executed successfully!")
            print(f"    Result type: {type(result.content)}")
            if result.content:
                content = result.content[0]
                if hasattr(content, 'text'):
                    paper_ids = json.loads(content.text)
                    print(f"    ✓ Found {len(paper_ids)} papers:")
                    for paper_id in paper_ids:
                        print(f"      - {paper_id}")
                else:
                    print(f"    Content: {content}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test extract_info tool
        print("\n[6] Testing extract_info tool...")
        # First, we need a paper ID from the previous search
        if 'paper_ids' in locals() and paper_ids:
            paper_id = paper_ids[0]
            print(f"    Extracting info for paper: {paper_id}")
            try:
                result = await session.call_tool(
                    "extract_info",
                    arguments={"paper_id": paper_id}
                )
                print(f"    ✓ Tool executed successfully!")
                if result.content:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        info = json.loads(content.text)
                        print(f"    Paper title: {info.get('title', 'N/A')[:60]}...")
                    else:
                        print(f"    Content: {content}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        else:
            print("    ⚠ Skipping - no paper IDs from previous search")
        
        # Test get_available_topics resource
        print("\n[7] Testing get_available_topics resource...")
        try:
            result = await session.read_resource("research://topics")
            print(f"    ✓ Resource read successfully!")
            if result.contents:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    print(f"    Content preview:\n{content.text[:200]}...")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        # Test get_topic_papers resource (if we have a topic)
        print("\n[8] Testing get_topic_papers resource...")
        topic_uri = "research://transformer_architectures"
        print(f"    Reading resource: {topic_uri}")
        try:
            result = await session.read_resource(topic_uri)
            print(f"    ✓ Resource read successfully!")
            if result.contents:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    print(f"    Content preview:\n{content.text[:300]}...")
        except Exception as e:
            print(f"    ⚠ Resource not found (expected if topic doesn't exist): {e}")
        
        print("\n" + "=" * 60)
        print("Integration tests complete!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mcp_server())

