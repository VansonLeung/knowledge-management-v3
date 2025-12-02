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
# Tool: polish_and_add_content
# =============================================================================
POLISH_AND_ADD_CONTENT_TOOL = _create_tool(
    name="polish_and_add_content",
    description=(
        "Polish a section of the original text and add it to the final output. "
        "Use this tool to clean up messy text extracted from web pages or documents. "
        "\n\n"
        "HOW TO USE:\n"
        "1. First read through the document using read_text to understand the content.\n"
        "2. For each meaningful section you find (30-50 lines at a time), call this tool.\n"
        "3. Provide the original line range (start_line, end_line) that contains the content.\n"
        "4. Provide a polished version of that section's text in polished_text.\n"
        "5. Skip sections that are boilerplate, navigation, ads, or unrelated content.\n"
        "\n"
        "POLISHING GUIDELINES:\n"
        "- Remove HTML artifacts, broken formatting, and unnecessary whitespace.\n"
        "- Fix obvious typos and formatting issues.\n"
        "- Restructure slightly for clarity if needed (combine fragmented sentences).\n"
        "- Preserve the original meaning and all important information.\n"
        "- Keep markdown formatting (headers, lists, emphasis) where appropriate.\n"
        "- Do NOT add new information or significantly rewrite the content.\n"
        "\n"
        "IMPORTANT:\n"
        "- Only use this tool AFTER YOU HAVE READ THE WHOLE DOCUMENT.\n"
        "- Only sections added with this tool will appear in the final output.\n"
        "- Process the document in order, section by section.\n"
        "- You may call this tool multiple times to build up the complete article.\n"
        "- The polished sections will be concatenated in the order you add them."
    ),
    parameters={
        "polished_text": {
            "type": "string",
            "description": (
                "The cleaned and polished version of the content from the specified lines. "
                "This should be well-formatted markdown text, free of HTML artifacts and "
                "formatting issues. Preserve all important information from the original."
            ),
        },
        "start_line": {
            "type": "integer",
            "description": "(Optional) Starting line number of the original content (1-indexed)",
        },
        "end_line": {
            "type": "integer",
            "description": "(Optional) Ending line number of the original content (1-indexed, inclusive)",
        },
        "section_label": {
            "type": "string",
            "description": (
                "Optional label for this section (e.g., 'introduction', 'main_content', "
                "'conclusion'). Helps track what type of content was extracted."
            ),
        },
    },
    required=["polished_text"],
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
            "description": "Detected language/locale (e.g., 'en-US', 'zh-CN', 'ja-JP', 'zh-HK')",
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
        "summary": {
            "type": "string",
            "description": "Concise summary of the document content",
        },
        "author": {
            "type": "string",
            "description": "Author of the main article, if known",
        },
        "published_by": {
            "type": "string",
            "description": "Publisher or source of the main article, if known",
        },
        "published_at": {
            "type": "string",
            "description": "Publication date/time in ISO 8601 format, if known",
        },
        "date_start": {
            "type": "string",
            "description": "Start date/time of the event described in the main article, in ISO 8601 format, if applicable",
        },
        "date_end": {
            "type": "string",
            "description": "End date/time of the event described in the main article, in ISO 8601 format, if applicable",
        },
        "date_duration": {
            "type": "string",
            "description": "Duration of the event described in the main article (e.g., '3 hours', '2 days'), if applicable",
        },
        "location": {
            "type": "string",
            "description": "Location of the event described in the main article, if applicable",
        },
        "venue": {
            "type": "string",
            "description": "Venue of the event described in the main article, if applicable",
        },
        "related_people": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Related list of people mentioned in the main article",
        },
        "related_organizations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Related list of organizations mentioned in the main article",
        },
        "related_links": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of related URLs mentioned in the document",
        },
    },
    required=["language", "title", "keywords", "category"],
)


# =============================================================================
# All Tools
# =============================================================================
ALL_TOOLS: List[ToolDefinition] = [
    READ_TEXT_TOOL,
    POLISH_AND_ADD_CONTENT_TOOL,
    LOOKUP_GLOSSARY_TOOL,
    FINISH_ANALYSIS_TOOL,
]


def get_tool_names(enable_polish_content: bool = True) -> List[str]:
    """Get list of available tool names.
    
    Args:
        enable_polish_content: Whether to include polish_and_add_content tool.
    """
    tools = get_tool_definitions(enable_polish_content)
    return [tool["function"]["name"] for tool in tools]


def get_tool_definitions(enable_polish_content: bool = True) -> List[ToolDefinition]:
    """Get the list of tool definitions for LLM function calling.
    
    Args:
        enable_polish_content: Whether to include polish_and_add_content tool.
            When False, the LLM will only read and analyze without polishing.
            
    Returns:
        List of tool definitions.
    """
    tools = [
        READ_TEXT_TOOL,
        LOOKUP_GLOSSARY_TOOL,
        FINISH_ANALYSIS_TOOL,
    ]
    
    if enable_polish_content:
        # Insert after READ_TEXT_TOOL
        tools.insert(1, POLISH_AND_ADD_CONTENT_TOOL)
    
    return tools
