"""Tool definitions for LLM function calling.

Defines the available tools that the LLM agent can use during analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Type alias for tool definition
ToolDefinition = Dict[str, Any]


def _create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    required: List[str],
) -> ToolDefinition:
    """Create a tool definition in OpenAI function calling format."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


# =============================================================================
# Tool: read_text
# =============================================================================
READ_TEXT_TOOL = _create_tool(
    name="read_text",
    description=(
        "Read specific lines from the text. Returns line-numbered text "
        "for the requested range plus a few lines of context before and after. "
        "For very long single-line texts, use line_offset_character_count to "
        "treat every N characters as a virtual line. "
        "Suggested line window size should not be smaller than 50 lines. "
    ),
    parameters={
        "start_line": {
            "type": "integer",
            "description": "Starting line number (1-indexed)",
        },
        "end_line": {
            "type": "integer",
            "description": "Ending line number (1-indexed, inclusive)",
        },
    },
    required=["start_line", "end_line"],
)



# =============================================================================
# Tool: extract_lines_as_main_article
# =============================================================================
EXTRACT_LINES_AS_MAIN_ARTICLE_TOOL = _create_tool(
    name="extract_lines_as_main_article",
    description=(
        "Mark a range of lines as main article content to be included in the final output. "
        "Only lines extracted with this tool will appear in the final cleaned content. "
        "You muse use this to pick relevant content, including the main article, "
        "article headers and footers, and exclude boilerplate, "
        "navigation, advertisements, unrelated links or other irrelevant text. "
        "IMPORTANT: You MUST read through the ENTIRE document first (using read_text) "
        "before starting to extract lines. This ensures you understand the full context "
        "and can make accurate extraction decisions. "
        "Line numbers remain stable - extracting lines does not change the document structure."
        "You must extract all relevant lines for the main article accurately. "
        "Failing to do so will result in incomplete or incorrect final content. "
        "You should use this tool several times (instead of once) as needed "
        "to cover all relevant sections when the contents are scattered."
    ),
    parameters={
        "start_line": {
            "type": "integer",
            "description": "Starting line number (1-indexed)",
        },
        "end_line": {
            "type": "integer",
            "description": "Ending line number (1-indexed, inclusive)",
        },
    },
    required=["start_line", "end_line"],
)


# =============================================================================
# Tool: lookup_glossary
# =============================================================================
LOOKUP_GLOSSARY_TOOL = _create_tool(
    name="lookup_glossary",
    description=(
        "Look up terms in the provided glossary. "
        "Returns definitions for matching terms."
    ),
    parameters={
        "terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of terms to look up",
        },
    },
    required=["terms"],
)


# =============================================================================
# Tool: finish_analysis
# =============================================================================
FINISH_ANALYSIS_TOOL = _create_tool(
    name="finish_analysis",
    description=(
        "Complete the analysis and provide final results. "
        "Call this when you have finished analyzing the text."
    ),
    parameters={
        "language": {
            "type": "string",
            "description": "Detected language/locale (e.g., 'en-US', 'zh-CN', 'ja-JP')",
        },
        "title": {
            "type": "string",
            "description": "Inferred or extracted title of the document",
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Generated keywords that capture the main topics",
        },
        "category": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Hierarchical category path, e.g., ['Technology', 'AI', 'NLP']",
        },
    },
    required=["language", "title", "keywords", "category"],
)


# =============================================================================
# All Tools
# =============================================================================
ALL_TOOLS: List[ToolDefinition] = [
    READ_TEXT_TOOL,
    EXTRACT_LINES_AS_MAIN_ARTICLE_TOOL,
    LOOKUP_GLOSSARY_TOOL,
    FINISH_ANALYSIS_TOOL,
]


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return [tool["function"]["name"] for tool in ALL_TOOLS]


def get_tool_definitions() -> List[ToolDefinition]:
    """Get the full list of tool definitions for LLM function calling."""
    return ALL_TOOLS
