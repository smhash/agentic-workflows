# ResearchAgent MCP

A fully functional research agent that searches and analyzes academic papers and uses them to respond to user questions. This project consists of a research server that provides tools for searching and managing academic papers, and a research client that uses OpenAI's GPT API to interact with users and perform research tasks.

## Features

- **Research Server**: MCP server that provides tools for:
  - Searching papers on arXiv by topic
  - Extracting information about specific papers
  - Accessing papers by topic through resources
  - Web search via Tavily API
  - Wikipedia search
  - arXiv paper search

- **Research Client**: Interactive research assistant that:
  - Connects to multiple MCP servers
  - Uses OpenAI GPT for natural language interactions
  - Automatically calls MCP tools when needed
  - Supports resource access

- **Multi-Agent Workflow**: Orchestrated research system with specialized agents:
  - **PlannerAgent**: Generates step-by-step research plans
  - **ResearchAgent**: Executes research tasks using MCP tools
  - **WriterAgent**: Drafts and summarizes research content
  - **EditorAgent**: Critiques and revises content
  - **ResearchOrchestratorAgent**: Orchestrates the complete workflow

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd researchagent-mcp
```

2. Install dependencies using uv:
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here  # Optional, for web search
```

## Configuration

The project uses `server_config.json` to configure MCP servers. The default configuration includes:

- **research**: The local research server (runs `research_mcp_server.py`)
- **filesystem**: Filesystem MCP server (via npx)
- **fetch**: Fetch MCP server (via uvx)

You can modify `server_config.json` to add or remove servers as needed.

## Usage

### Running the Multi-Agent Workflow

To run the multi-agent research workflow application:

```bash
uv run research-workflow
```

**Note:** The `uv run` command is required. This ensures the application runs with the correct dependencies from the project's virtual environment.

If you have installed the package globally, you can also run:
```bash
research-workflow
```

However, using `uv run research-workflow` is the recommended approach as it automatically manages the environment.

### Running the Research Server

The research server is typically started automatically by the MCP client, but you can also run it directly:

```bash
uv run research-server
```

Or if installed:
```bash
research-server
```

### Using MCP Inspector

MCP Inspector is a web-based tool for testing and debugging MCP servers. To use it with the research server:

1. **Install and run MCP Inspector:**
   ```bash
   npx -y @modelcontextprotocol/inspector
   ```

2. **Configure the server in the Inspector UI:**
   - **Transport Type**: Select `stdio`
   - **Command**: Enter `uv`
   - **Arguments**: Enter `run src/research_mcp_server.py` (space-separated)

3. **Alternative: Use the config file:**
   ```bash
   npx -y @modelcontextprotocol/inspector --config inspector_config.json
   ```

Once connected, you can:
- View all available tools (`arxiv_search`, `extract_info`)
- Test tools with different parameters
- Access resources (`research://topics`, `research://{topic}`)

### Research Workflow Commands

Once the research workflow application is running, you can use the following commands:

- **Research topics**: Type a research topic and the multi-agent research workflow will execute a complete research plan
- **`@topics`**: List all available research topics
- **`@<topic>`**: View papers for a specific topic (e.g., `@ai_interpretability`)
- **`quit`** or **`exit`**: Exit the research workflow application

### Example Usage

```
Query: transformer architectures
Query: @topics
Query: @llm_reasoning
Query: neural networks
Query: quit
```

### Multi-Agent Research Workflow

The project includes a sophisticated multi-agent system for automated research workflows. This system orchestrates multiple specialized agents to complete complex research tasks.

#### Architecture

The research workflow consists of five specialized agents:

1. **PlannerAgent** (`src/planner_agent.py`):
   - Generates structured, step-by-step research plans
   - Outputs plans as Python lists of executable tasks
   - Ensures plans only reference available agent capabilities

2. **ResearchAgent** (`src/research_agent.py`):
   - Executes research tasks using MCP tools
   - Dynamically discovers and uses tools from the MCP server
   - Supports: arXiv search, Tavily web search, Wikipedia search
   - Returns structured research summaries

3. **WriterAgent** (`src/writer_agent.py`):
   - Drafts research summaries and content
   - Synthesizes information from multiple sources
   - Formats output as Markdown documents

4. **EditorAgent** (`src/editor_agent.py`):
   - Critiques and revises content
   - Improves clarity, accuracy, and structure
   - Provides feedback and refined versions

5. **ResearchOrchestratorAgent** (`src/research_orchestrator_agent.py`):
   - Orchestrates the complete workflow
   - Routes tasks to appropriate agents
   - Manages context and execution history
   - Handles agent coordination and decision-making

#### Usage

```python
import asyncio
from src.research_orchestrator_agent import ResearchOrchestratorAgent

async def main():
    orchestrator = ResearchOrchestratorAgent()
    
    try:
        history = await orchestrator.orchestrate_research_workflow(
            topic="The ensemble Kalman filter for time series forecasting",
            model="gpt-4o",
            limit_steps=False,  # Run full research workflow
            max_steps=10
        )
        
        # Access execution history
        for step, agent_name, output in history:
            print(f"{agent_name}: {output[:100]}...")
            
    finally:
        await orchestrator.cleanup()

asyncio.run(main())
```

**With Custom MCP Client:**

```python
from src.utils.mcp_client import MCPClient
from src.research_orchestrator_agent import ResearchOrchestratorAgent

async def main():
    mcp_client = MCPClient()
    await mcp_client.connect_to_servers()
    
    orchestrator = ResearchOrchestratorAgent(
        mcp_client=mcp_client
    )
    
    history = await orchestrator.orchestrate_research_workflow(topic="...")
    await orchestrator.cleanup()
```

#### Research Workflow Process

1. **Planning Phase**: PlannerAgent generates a research plan
2. **Execution Phase**: ResearchOrchestratorAgent routes each step to the appropriate agent:
   - Research tasks → ResearchAgent
   - Writing tasks → WriterAgent
   - Editing tasks → EditorAgent
3. **Context Management**: Each agent's output becomes context for subsequent steps
4. **Completion**: Final output is typically a Markdown research report

#### Testing

Run the multi-agent workflow test:

```bash
uv run python tests/test_multi_agent_workflow.py
```

Or run all tests:

```bash
uv run pytest tests/
```

## Project Structure

```
researchagent-mcp/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py                  # Main application entry point
│   ├── research_mcp_server.py   # MCP research server implementation
│   ├── mcp_client.py            # MCP client - manages server connections
│   ├── chat_interface.py        # Chat interface - handles user interaction
│   ├── planner_agent.py         # PlannerAgent - generates research plans
│   ├── research_agent.py          # ResearchAgent - executes research tasks
│   ├── writer_agent.py           # WriterAgent - drafts content
│   ├── editor_agent.py           # EditorAgent - critiques and revises
│   └── research_orchestrator_agent.py # ResearchOrchestratorAgent - orchestrates workflow
├── tests/                  # Test files
│   ├── __init__.py
│   ├── test_integration.py      # Integration tests (real arXiv calls)
│   ├── test_server.py           # Direct function tests
│   ├── test_research_agent.py   # Unit tests for MCP client
│   ├── test_e2e.py              # End-to-end tests
│   ├── test_chat_loop.py        # Chat interface tests
│   ├── test_multi_agent_workflow.py # Multi-agent workflow tests
│   └── TESTING.md               # Testing guide
├── research_papers/       # Directory for stored paper information
│   ├── ai_interpretability/
│   │   └── raw/
│   │       ├── 1706.03138v1.json
│   │       └── ...
│   ├── llm_reasoning/
│   │   └── raw/
│   │       ├── 2301.12299v1.json
│   │       └── ...
│   ├── machine_learning/
│   │   └── raw/
│   │       ├── 2401.12345v1.json
│   │       └── ...
│   └── transformer_architectures/
│       └── raw/
│           └── ...
├── server_config.json      # MCP server configuration
├── inspector_config.json   # MCP Inspector configuration
├── pyproject.toml          # Project dependencies and metadata
├── requirements.txt        # Python dependencies (generated)
├── uv.lock                 # Lock file for uv
├── README.md               # This file
└── .env.example            # Environment variables template
```

## How It Works

1. **Research Server** (`research_mcp_server.py`):
   - Implements an MCP server using FastMCP
   - Provides tools: `arxiv_search`, `extract_info`
   - Provides resources: `research://topics`, `research://{topic}`
   - Stores individual papers as JSON files in `research_papers/{topic}/raw/{paper_id}.json`

2. **MCP Client** (`mcp_client.py`):
   - Manages connections to MCP servers
   - Discovers and caches available tools and resources
   - Maps capabilities to server sessions
   - Handles session lookup for tool and resource execution

3. **Chat Interface** (`chat_interface.py`):
   - Handles user interaction and command parsing
   - Processes special commands (`@topics`, `@<topic>`, etc.)
   - Provides the interactive chat loop
   - Separates UI concerns from business logic

5. **Multi-Agent System**:
   - **PlannerAgent**: Uses GPT to generate structured research plans
   - **ResearchAgent**: Dynamically discovers and uses MCP tools for research
   - **WriterAgent**: Synthesizes research findings into coherent content
   - **EditorAgent**: Refines and improves content quality
   - **ResearchOrchestratorAgent**: Routes tasks, manages context, and orchestrates the workflow

## Development

To contribute or modify the project:

1. Install development dependencies (if any)
2. Make your changes
3. Test locally using `uv run research-workflow`

## Dependencies

- `openai`: OpenAI API client
- `arxiv`: arXiv API client for paper search
- `mcp`: Model Context Protocol SDK
- `nest-asyncio`: Allows nested event loops
- `python-dotenv`: Environment variable management
- `tavily-python`: Tavily API client for web search (optional)
- `wikipedia`: Wikipedia API client for encyclopedic knowledge
- `requests`: HTTP library for API calls

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

