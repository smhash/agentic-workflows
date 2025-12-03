"""MCP Server for research tools - provides arXiv, Tavily, and Wikipedia search capabilities."""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import arxiv
import requests
import wikipedia

try:
    from pypdf import PdfReader
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_EXTRACTION_AVAILABLE = False
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Constants
RESEARCH_PAPER_DIR = Path("research_papers")
RAW_PAPERS_DIR = "raw"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

# Initialize FastMCP server
mcp = FastMCP("research")

def _normalize_topic(topic: str) -> str:
    """Normalize topic name for use in file paths."""
    return topic.lower().replace(" ", "_")


def _get_topic_dir(topic: str) -> Path:
    """Get the directory path for a topic."""
    return RESEARCH_PAPER_DIR / _normalize_topic(topic)


def _get_raw_papers_dir(topic: str) -> Path:
    """Get the raw papers directory path for a topic."""
    return _get_topic_dir(topic) / RAW_PAPERS_DIR


def _get_document_file(topic: str, source: str, doc_id: str) -> Path:
    """Get the document file path for a topic, source, and document ID."""
    filename = f"{source}_{doc_id}.json"
    return _get_raw_papers_dir(topic) / filename


def _normalize_document(data: Dict[str, Any], source: str, query: str) -> Dict[str, Any]:
    """
    Wrap document with unified schema, flattening for easy access.
    
    Args:
        data: Source-specific document data
        source: Document source ("arxiv", "wikipedia", "tavily")
        query: Original search query
        
    Returns:
        Unified document structure with common fields at top level
    """
    # Extract common fields based on source
    title = data.get("title", "")
    url = data.get("url") or data.get("pdf_url") or data.get("entry_id", "")
    # Prefer full text > content > summary for better synthesis
    content = data.get("full_text") or data.get("content") or data.get("summary", "")
    
    # Build unified document
    unified = {
        "source": source,
        "query": query,
        "fetched_at": datetime.now().isoformat(),
        "title": title,
        "url": url,
        "content": content,
    }
    
    # Merge all source-specific fields (preserve everything)
    return {**unified, **data}


def _generate_document_id(source: str, data: Dict[str, Any]) -> str:
    """
    Generate a unique document ID based on source and data.
    
    Args:
        source: Document source ("arxiv", "wikipedia", "tavily")
        data: Document data
        
    Returns:
        Unique identifier string
    """
    if source == "arxiv":
        # Use paper short ID
        return data.get("paper_id") or data.get("entry_id", "").split("/")[-1]
    elif source == "wikipedia":
        # Normalize title for filename
        title = data.get("title", "")
        return _normalize_topic(title)
    elif source == "tavily":
        # Hash URL for uniqueness
        url = data.get("url", "")
        return hashlib.md5(url.encode()).hexdigest()[:12]
    else:
        # Fallback: hash the entire data
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()[:12]


def _load_paper(file_path: Path) -> Dict[str, Any]:
    """Load a single paper from JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_paper(file_path: Path, paper_info: Dict[str, Any]) -> None:
    """Save a single paper to JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(paper_info, f, indent=2)


@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific document across all topic directories.
    Searches all document types (arxiv, wikipedia) using source_id.json format.
    
    Args:
        paper_id: The ID of the document to look for.
        
    Returns:
        JSON string with document information if found, error message otherwise.
    """
    if not RESEARCH_PAPER_DIR.exists():
        return f"There's no saved information related to document {paper_id}."
    
    # Search all topic directories for raw document files
    for topic_dir in RESEARCH_PAPER_DIR.iterdir():
        if not topic_dir.is_dir():
            continue
        
        raw_dir = topic_dir / RAW_PAPERS_DIR
        if not raw_dir.exists():
            continue
        
        # Search all files and match by ID in document content or filename
        for doc_file in raw_dir.glob("*.json"):
            doc_info = _load_paper(doc_file)
            if doc_info:
                # Check if paper_id matches any ID field in the document or filename
                doc_id = doc_info.get("paper_id") or doc_info.get("id") or ""
                if paper_id in str(doc_id) or paper_id in doc_file.stem:
                    return json.dumps(doc_info, indent=2)
    
    return f"There's no saved information related to document {paper_id}."



@mcp.resource("research://topics")
def get_available_topics() -> str:
    """
    List all available research topic folders.
    
    Returns:
        JSON string with list of topics, each containing name and paper_count.
    """
    if not RESEARCH_PAPER_DIR.exists():
        return json.dumps({"topics": []}, indent=2)
    
    topics_list = []
    for topic_dir in RESEARCH_PAPER_DIR.iterdir():
        if not topic_dir.is_dir():
            continue
        
        raw_dir = topic_dir / RAW_PAPERS_DIR
        if not raw_dir.exists():
            continue
        
        paper_files = list(raw_dir.glob("*.json"))
        if paper_files:
            topics_list.append({
                "name": topic_dir.name,
                "paper_count": len(paper_files)
            })
    
    return json.dumps({"topics": topics_list}, indent=2)

def _format_document_markdown(doc: Dict[str, Any], max_content_length: int = 8000) -> str:
    """
    Format any document type (arxiv/wikipedia) as markdown.
    
    Args:
        doc: Document dictionary
        max_content_length: Maximum length of content to include (to avoid token limits)
    """
    source = doc.get("source", "unknown")
    title = doc.get("title", "Untitled")
    content_text = doc.get("content", "")
    url = doc.get("url", "")
    
    # Truncate content if too long to avoid token limit issues
    # Keep full text in storage, but limit what we send to WriterAgent
    original_length = len(content_text)
    if len(content_text) > max_content_length:
        # For long content, include abstract + truncated full text
        summary = doc.get("summary", "")
        if summary and source == "arxiv":
            # Use abstract + first part of full text
            remaining_chars = max_content_length - len(summary) - 500  # Reserve space
            if remaining_chars > 0:
                truncated = content_text[:remaining_chars]
                content_text = f"{summary}\n\n[Full text truncated for length - showing first {remaining_chars:,} characters of {original_length:,} total]\n\n{truncated}..."
            else:
                content_text = summary
        else:
            # Just truncate
            content_text = content_text[:max_content_length] + f"...\n\n[Content truncated - showing first {max_content_length:,} characters of {original_length:,} total]"
    
    # Start with title and source
    markdown = f"## {title}\n\n"
    markdown += f"- **Source**: {source.upper()}\n"
    
    if url:
        markdown += f"- **URL**: [{url}]({url})\n"
    
    # Source-specific formatting
    if source == "arxiv":
        if doc.get("authors"):
            markdown += f"- **Authors**: {', '.join(doc['authors'])}\n"
        if doc.get("published"):
            markdown += f"- **Published**: {doc['published']}\n"
        if doc.get("updated"):
            markdown += f"- **Updated**: {doc['updated']}\n"
        if doc.get("pdf_url"):
            markdown += f"- **PDF**: [{doc['pdf_url']}]({doc['pdf_url']})\n"
        if doc.get("doi"):
            markdown += f"- **DOI**: {doc['doi']}\n"
        if doc.get("primary_category"):
            markdown += f"- **Category**: {doc['primary_category']}\n"
        # Show full text length if available
        if doc.get("full_text_length"):
            markdown += f"- **Full Text Length**: {doc['full_text_length']:,} characters (stored)\n"
        # Show content (may be truncated if too long)
        markdown += f"\n### Content\n{content_text}\n\n"
    
    elif source == "wikipedia":
        if doc.get("content_length"):
            markdown += f"- **Content Length**: {doc['content_length']} characters\n"
        # Show summary if available and different from content
        summary = doc.get("summary", "")
        if summary and summary != content_text:
            markdown += f"\n### Summary\n{summary}\n\n"
        markdown += f"\n### Full Content\n{content_text}\n\n"
    
    elif source == "tavily":
        if doc.get("score") is not None:
            markdown += f"- **Relevance Score**: {doc['score']:.2f}\n"
        markdown += f"\n### Content\n{content_text}\n\n"
    
    else:
        # Generic fallback
        markdown += f"\n### Content\n{content_text}\n\n"
    
    markdown += "---\n\n"
    return markdown


@mcp.resource("research://{topic}")
def get_topic_papers(topic: str) -> str:
    """
    Get detailed information about research on a specific topic.
    Returns full paper content including complete summaries and all metadata.
    
    Args:
        topic: The research topic to retrieve information for.
        
    Returns:
        Markdown-formatted content with full paper details including complete summaries.
    """
    raw_dir = _get_raw_papers_dir(topic)
    
    if not raw_dir.exists():
        return f"# No papers found for topic: {topic}\n\nTry searching for papers on this topic first using arxiv_search."
    
    # Load all document files from raw directory - ensure we get ALL files
    doc_files = list(raw_dir.glob("*.json"))
    if not doc_files:
        return f"# No documents found for topic: {topic}\n\nTry searching for documents on this topic first using arxiv_search, tavily_search, or wikipedia_search."
    
    try:
        topic_title = topic.replace('_', ' ').title()
        
        # Load ALL documents from raw folder - ensure nothing is skipped
        all_docs = []
        sources = {}
        failed_files = []
        
        for doc_file in doc_files:
            doc = _load_paper(doc_file)
            if doc and doc.get("content") or doc.get("summary"):
                # Only include documents that have actual content
                all_docs.append((doc_file, doc))
                source = doc.get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1
            else:
                # Track files that couldn't be loaded or have no content
                failed_files.append(doc_file.name)
        
        if failed_files:
            print(f"⚠️ Skipped {len(failed_files)} files with no content: {failed_files}")
        
        source_summary = ", ".join([f"{count} {source}" for source, count in sorted(sources.items())])
        content = f"# Documents on {topic_title}\n\nTotal documents: {len(all_docs)} ({source_summary})\n\n"
        
        # Sort documents by priority: arXiv first, then Wikipedia, then others
        def sort_key(item):
            doc_file, doc = item
            source = doc.get("source", "unknown")
            # Priority: arxiv=0, wikipedia=1, tavily=2, other=3
            priority = {"arxiv": 0, "wikipedia": 1, "tavily": 2}.get(source, 3)
            return (priority, doc.get("title", ""))
        
        # Calculate per-document limit to stay under token budget
        # Reserve ~5K tokens for system prompt, context, and task
        # Target: ~25K tokens for documents, split across all docs
        target_total_tokens = 25000
        chars_per_token = 4  # Rough estimate
        target_total_chars = target_total_tokens * chars_per_token
        # Reserve some space for markdown formatting overhead
        per_doc_limit = max(5000, (target_total_chars // len(all_docs)) - 2000) if all_docs else 8000
        
        # Format all documents - ensure every document is included
        # Use per-document limit to stay under total token budget
        for doc_file, doc in sorted(all_docs, key=sort_key):
            content += _format_document_markdown(doc, max_content_length=per_doc_limit)
        
        return content
    except Exception as e:
        return f"# Error reading papers data for {topic}\n\nError: {str(e)}"

def _extract_pdf_text(pdf_url: str, timeout: int = 30) -> Optional[str]:
    """
    Download PDF from URL and extract text content.
    
    Args:
        pdf_url: URL to the PDF file
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text content, or None if extraction fails
    """
    if not PDF_EXTRACTION_AVAILABLE:
        return None
    
    try:
        # Download PDF
        response = requests.get(pdf_url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Extract text from PDF
        from io import BytesIO
        pdf_bytes = BytesIO(response.content)
        reader = PdfReader(pdf_bytes)
        
        # Extract text from all pages
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        full_text = "\n\n".join(text_parts)
        return full_text if full_text.strip() else None
    except Exception as e:
        print(f"⚠️ PDF extraction failed for {pdf_url}: {e}")
        return None


def _extract_arxiv_paper_info(paper: arxiv.Result, extract_full_text: bool = True) -> Dict[str, Any]:
    """
    Extract all available information from an arXiv paper result.
    
    Args:
        paper: arXiv paper result object
        extract_full_text: If True, attempt to extract full text from PDF
        
    Returns:
        Dictionary with paper information including full text if extraction succeeds
    """
    paper_info = {
        "title": paper.title,
        "authors": [author.name for author in paper.authors],
        "summary": paper.summary,  # Abstract/summary
        "pdf_url": paper.pdf_url,
        "entry_id": paper.entry_id,
        "published": str(paper.published.date()) if paper.published else None,
        "updated": str(paper.updated.date()) if paper.updated else None,
        "comment": paper.comment if hasattr(paper, 'comment') and paper.comment else None,
        "journal_ref": paper.journal_ref if hasattr(paper, 'journal_ref') and paper.journal_ref else None,
        "doi": paper.doi if hasattr(paper, 'doi') and paper.doi else None,
        "primary_category": str(paper.primary_category) if paper.primary_category else None,
        "categories": [str(cat) for cat in paper.categories] if paper.categories else [],
        "links": [{"href": link.href, "rel": link.rel, "title": getattr(link, 'title', None)} for link in paper.links] if hasattr(paper, 'links') and paper.links else []
    }
    
    # Attempt to extract full text from PDF if requested
    if extract_full_text and paper.pdf_url:
        print(f"📄 Extracting full text from PDF: {paper.pdf_url}")
        full_text = _extract_pdf_text(paper.pdf_url)
        if full_text:
            paper_info["full_text"] = full_text
            paper_info["full_text_length"] = len(full_text)
            print(f"✅ Extracted {len(full_text)} characters from PDF")
        else:
            print("⚠️ Could not extract full text, using abstract only")
    
    return paper_info


@mcp.tool()
def arxiv_search(query: str, max_results: int = 5, topic: str = None) -> str:
    """
    Searches for research papers on arXiv by query string.
    Uses the arxiv library for reliable parsing and returns comprehensive paper data.
    Automatically stores papers for later retrieval via resources.
    
    Args:
        query: Search keywords for research papers.
        max_results: Maximum number of results to return (default: 5).
        topic: Optional topic name for document storage. If not provided, derived from query.
        
    Returns:
        JSON string with list of paper dictionaries containing comprehensive information:
        title, authors, summary (full content), pdf_url, entry_id, published, updated,
        comment, journal_ref, doi, primary_category, categories, and links.
        
    Note:
        Papers are automatically stored in research_papers/{normalized_topic}/raw/{paper_id}.json
        where the topic name is either provided or derived from the query by normalizing it.
    """
    try:
        # Use provided topic or derive from query
        storage_topic = _normalize_topic(topic) if topic else _normalize_topic(query)
        
        # Use arxiv library for reliable search and parsing
        arxiv_client = arxiv.Client()
        search_criteria = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        papers_list = list(arxiv_client.results(search_criteria))
        
        # Extract full paper information and store
        results = []
        raw_dir = _get_raw_papers_dir(storage_topic)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        for i, paper in enumerate(papers_list):
            paper_id = paper.get_short_id()
            # Add small delay between PDF downloads to be respectful to arXiv servers
            # (arXiv requests avoiding automated bulk downloads)
            if i > 0:
                time.sleep(1)  # 1 second delay between downloads
            # Extract paper info with full text from PDF
            paper_info = _extract_arxiv_paper_info(paper, extract_full_text=True)
            
            # Add fields needed for unified schema and document ID generation
            paper_info["url"] = paper.entry_id
            paper_info["link_pdf"] = paper.pdf_url
            paper_info["paper_id"] = paper_id
            
            # Use full text if available, otherwise fall back to summary
            if paper_info.get("full_text"):
                paper_info["content"] = paper_info["full_text"]
            else:
                paper_info["content"] = paper_info["summary"]
            
            # Wrap with unified schema
            unified_doc = _normalize_document(paper_info, "arxiv", query)
            
            # For API response, return original structure
            results.append(paper_info)
            
            # Store with unified schema
            doc_id = _generate_document_id("arxiv", unified_doc)
            doc_file = _get_document_file(storage_topic, "arxiv", doc_id)
            _save_paper(doc_file, unified_doc)
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps([{"error": f"arXiv search failed: {str(e)}"}])


@mcp.tool()
def tavily_search(query: str, max_results: int = 5, topic: str = None) -> str:
    """
    Performs a general-purpose web search using the Tavily API.
    
    Args:
        query: Search keywords for retrieving information from the web.
        max_results: Maximum number of results to return (default: 5).
        topic: Optional topic name for document storage. If not provided, derived from query.
        
    Returns:
        JSON string with search results including titles, URLs, and content (snippets from Search API, with full content attempted via Extract API when available).
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not found in environment variables"})
    
    try:
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic"
        }
        
        response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract full content for each result using Tavily Extract API
        results = []
        for result in data.get("results", []):
            url = result.get("url", "")
            snippet = result.get("content", "")
            
            # Try to get full content from Extract API
            full_content = snippet
            if url and api_key:
                try:
                    # Skip extraction for video URLs (YouTube, etc.) - they won't have extractable text
                    if any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'vimeo.com']):
                        # Keep snippet for videos
                        pass
                    else:
                        extract_payload = {
                            "api_key": api_key,
                            "url": url,
                            "extraction_mode": "advanced"  # Get comprehensive content
                        }
                        extract_response = requests.post(TAVILY_EXTRACT_URL, json=extract_payload, timeout=15)
                        if extract_response.status_code == 200:
                            extract_data = extract_response.json()
                            extracted_content = extract_data.get("content", "")
                            # Only use extracted content if it's significantly longer than snippet
                            if extracted_content and len(extracted_content) > len(snippet) * 1.5:
                                full_content = extracted_content
                except Exception as e:
                    # Log but continue with snippet
                    print(f"⚠️ Tavily Extract API failed for {url}: {e}")
            
            results.append({
                "title": result.get("title", ""),
                "url": url,
                "content": full_content,
                "score": result.get("score", 0)
            })
        
        # Store each result with unified schema
        # Use provided topic or derive from query
        storage_topic = _normalize_topic(topic) if topic else _normalize_topic(query)
        raw_dir = _get_raw_papers_dir(storage_topic)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        for result in results:
            unified_doc = _normalize_document(result, "tavily", query)
            doc_id = _generate_document_id("tavily", unified_doc)
            doc_file = _get_document_file(storage_topic, "tavily", doc_id)
            _save_paper(doc_file, unified_doc)
        
        return json.dumps({"query": query, "results": results}, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Tavily search failed: {str(e)}"})


@mcp.tool()
def wikipedia_search(query: str, topic: str = None) -> str:
    """
    Searches for a Wikipedia article summary by query string.
    
    Args:
        query: Search keywords for the Wikipedia article.
        topic: Optional topic name for document storage. If not provided, derived from query.
        
    Returns:
        JSON string with Wikipedia page title, summary, and URL.
    """
    wikipedia.set_lang("en")
    
    try:
        search_results = wikipedia.search(query, results=1)
        if not search_results:
            return json.dumps({"error": f"No Wikipedia page found for '{query}'"})
        
        page = wikipedia.page(search_results[0], auto_suggest=False)
        result = {
            "title": page.title,
            "url": page.url,
            "summary": page.summary,
            "content": page.content,
            "content_length": len(page.content)
        }
        
        # Store with unified schema
        # Use provided topic or derive from query
        storage_topic = _normalize_topic(topic) if topic else _normalize_topic(query)
        unified_doc = _normalize_document(result, "wikipedia", query)
        doc_id = _generate_document_id("wikipedia", unified_doc)
        raw_dir = _get_raw_papers_dir(storage_topic)
        raw_dir.mkdir(parents=True, exist_ok=True)
        doc_file = _get_document_file(storage_topic, "wikipedia", doc_id)
        _save_paper(doc_file, unified_doc)
        
        return json.dumps(result, indent=2)
        
    except wikipedia.DisambiguationError as e:
        options = e.options[:5]
        return json.dumps({
            "error": f"Disambiguation page for '{query}'",
            "options": options,
            "message": f"Please be more specific. Options: {', '.join(options)}"
        })
    except wikipedia.PageError:
        return json.dumps({"error": f"Wikipedia page '{query}' does not exist"})
    except Exception as e:
        return json.dumps({"error": f"Wikipedia search failed: {str(e)}"})

def main() -> None:
    """Entry point for the research MCP server."""
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()

