# Testing Guide

This guide explains how to test the research server with real arXiv API calls and using MCP Inspector.

## Integration Tests (Real arXiv Calls)

Run integration tests that make actual calls to the arXiv API via the MCP protocol:

```bash
python tests/test_integration.py
```

or

```bash
uv run python tests/test_integration.py
```

**Note:** Run from the project root directory.

This will:
- Connect to the MCP server via stdio
- List all available tools, resources, and prompts
- Test `arxiv_search` with a real arXiv API call
- Test `extract_info` for a retrieved paper
- Test resource access (`research://topics` and `research://{topic}`)
- Test prompt generation

## Using MCP Inspector

MCP Inspector is a web-based tool for testing and debugging MCP servers. It provides a visual interface to interact with your server.

### Installation

MCP Inspector is installed automatically via npx when you run it (no manual installation needed).

### Running MCP Inspector

1. **Create an inspector config file** (`inspector_config.json`):

```json
{
  "mcpServers": {
    "research": {
      "command": "uv",
      "args": ["run", "src/research_mcp_server.py"]
    }
  }
}
```

2. **Run the inspector**:

```bash
npx -y @modelcontextprotocol/inspector
```

Or with a specific config file:

```bash
npx -y @modelcontextprotocol/inspector --config inspector_config.json
```

3. **Use the web interface**:
   - The inspector will open in your browser (typically at `http://localhost:5173`)
   - You can see all available tools, resources, and prompts
   - Test tools by calling them with different parameters
   - View resource contents
   - Execute prompts

### Example Inspector Workflow

1. Start the inspector
2. In the web UI, you'll see the "research" server listed
3. Click on "Tools" to see `arxiv_search` and `extract_info`
4. Test `arxiv_search`:
   - Click on the tool
   - Enter parameters: `{"query": "quantum computing", "max_results": 5, "topic": "quantum_computing"}`
   - Click "Call Tool"
   - See the results (full paper data in JSON format)
5. Test `extract_info`:
   - Use one of the paper IDs from the previous search
   - Enter: `{"paper_id": "2301.12345"}`
   - See the paper information
6. Check Resources:
   - Click on "Resources"
   - View `research://topics` to see available topics
   - View `research://{topic}` for specific topics

## Direct Function Tests

For quick testing without the MCP protocol layer:

```bash
python tests/test_server.py
```

**Note:** Run from the project root directory.

This tests the functions directly (bypassing MCP) and is faster for development but doesn't test the MCP protocol integration.

## Test Coverage

- ✅ Real arXiv API calls (integration tests)
- ✅ MCP protocol communication
- ✅ Tool execution
- ✅ Resource access
- ✅ Prompt generation
- ✅ Error handling

## Troubleshooting

### Inspector won't start
- Make sure Node.js/npm is installed: `node --version`
- Try: `npx -y @modelcontextprotocol/inspector@latest`

### Server connection issues
- Check that `uv` is in your PATH
- Verify `src/research_mcp_server.py` is accessible
- Check Python version: `python --version` (needs 3.10+)

### arXiv API errors
- Check internet connection
- arXiv API has rate limits - wait a few seconds between tests
- Some queries may return no results (this is normal)

