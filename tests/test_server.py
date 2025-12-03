#!/usr/bin/env python3
"""Test script for research_mcp_server.py - tests functions directly without MCP protocol."""

import sys
from pathlib import Path

# Add src directory to path to import research_mcp_server
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from research_mcp_server import (
    extract_info,
    get_available_topics,
    get_topic_papers,
    arxiv_search
)

def test_arxiv_search():
    """Test searching for papers using arxiv_search."""
    print("Testing arxiv_search...")
    print("-" * 50)
    query = "machine learning"
    max_results = 3
    print(f"Searching for '{query}' with max_results={max_results}")
    
    try:
        result = arxiv_search(query=query, max_results=max_results)
        import json
        papers = json.loads(result)
        if isinstance(papers, list) and len(papers) > 0:
            print(f"✓ Found {len(papers)} papers:")
            for paper in papers[:3]:
                if "error" not in paper:
                    print(f"  - {paper.get('title', 'Unknown')[:60]}...")
            return papers
        return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []

def test_extract_info(paper_id: str = None):
    """Test extracting info for a specific paper."""
    print("\nTesting extract_info...")
    print("-" * 50)
    
    # If no paper_id provided, get one from a search
    if paper_id is None:
        result = arxiv_search(query="machine learning", max_results=1)
        import json
        papers = json.loads(result)
        if not papers or (isinstance(papers, list) and len(papers) == 0):
            print("⚠ No papers found to test with")
            return None
        paper = papers[0] if isinstance(papers, list) else {}
        if "error" in paper:
            print("⚠ Error in search results")
            return None
        paper_id = paper.get("paper_id") or paper.get("entry_id", "").split("/")[-1]
        if not paper_id:
            print("⚠ Could not extract paper ID")
            return None
    
    print(f"Extracting info for paper: {paper_id}")
    
    try:
        info = extract_info(paper_id)
        print(f"✓ Paper info retrieved:")
        print(info[:200] + "..." if len(info) > 200 else info)
        return info
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_get_available_topics():
    """Test getting available topics."""
    print("\nTesting get_available_topics...")
    print("-" * 50)
    
    try:
        content = get_available_topics()
        import json
        topics_data = json.loads(content)
        print("✓ Available topics:")
        if topics_data.get("topics"):
            for topic in topics_data["topics"]:
                print(f"  - {topic['name']} ({topic['paper_count']} papers)")
        else:
            print("  No topics found.")
        return topics_data
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_get_topic_papers(topic: str = "machine_learning"):
    """Test getting papers for a specific topic."""
    print(f"\nTesting get_topic_papers for topic: {topic}...")
    print("-" * 50)
    
    try:
        content = get_topic_papers(topic)
        print("✓ Topic papers:")
        print(content[:500] + "..." if len(content) > 500 else content)
        return content
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Research Server Functions")
    print("=" * 50)
    
    # Test search first
    papers = test_arxiv_search()
    
    # If we got papers, test extracting info from the first one
    if papers and isinstance(papers, list) and len(papers) > 0:
        paper = papers[0]
        if "error" not in paper:
            paper_id = paper.get("paper_id") or paper.get("entry_id", "").split("/")[-1]
            if paper_id:
                test_extract_info(paper_id)
    
    # Test getting available topics
    test_get_available_topics()
    
    # Test getting papers for a topic (using the topic we just searched)
    if paper_ids:
        test_get_topic_papers("machine learning")
    
    print("\n" + "=" * 50)
    print("Testing complete!")
    print("=" * 50)

