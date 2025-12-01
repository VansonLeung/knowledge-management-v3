"""System prompt generation for LLM analysis.

Builds dynamic system prompts based on document context,
available glossary entries, and category trees.
"""

from __future__ import annotations

from typing import List, Optional

from models import CategoryItem, CategoryNode


def _format_category_tree(
    categories: List[CategoryItem],
    indent: int = 0,
) -> str:
    """Recursively format a category tree for display.
    
    Args:
        categories: List of category items (strings or CategoryNode).
        indent: Current indentation level.
        
    Returns:
        Formatted tree string with proper indentation.
    """
    result = []
    prefix = "  " * indent
    
    for item in categories:
        if isinstance(item, str):
            result.append(f"{prefix}- {item}")
        elif isinstance(item, CategoryNode):
            result.append(f"{prefix}- {item.name}")
            if item.children:
                child_text = _format_category_tree(item.children, indent + 1)
                result.append(child_text)
    
    return "\n".join(result)


def build_system_prompt(
    total_lines: int,
    total_characters: int,
    has_glossary: bool,
    categories: Optional[List[CategoryItem]] = None,
    max_keywords: int = 10,
) -> str:
    """Build the system prompt for document analysis.
    
    Args:
        total_lines: Total number of lines in the document.
        total_characters: Total number of characters in the document.
        has_glossary: Whether a glossary is available.
        categories: Optional category tree for classification.
        max_keywords: Maximum number of keywords to generate.
        
    Returns:
        Complete system prompt string.
    """
    # Base instructions
    prompt_parts = [
        "You are a document analysis assistant. Analyze the provided text using the available tools.",
        "",
        f"The document has {total_lines} lines, {total_characters} characters.",
        "",
        "## Your Tasks",
        "",
        "1. **Read** the document section by section using `read_text`",
        "2. **Extract** main article lines using `extract_lines_as_main_article`",
    ]
    
    # Glossary instruction
    if has_glossary:
        prompt_parts.append(
            "3. **Look up** technical terms in the glossary using `lookup_glossary`"
        )
        next_step = 4
    else:
        next_step = 3
    
    prompt_parts.append(
        f"{next_step}. **Finish** with language, title, keywords, and category using `finish_analysis`"
    )
    
    # Detailed guidelines
    prompt_parts.extend([
        "",
        "## Guidelines",
        "",
        "### Content Removal",
        "Remove these types of content:",
        "- Table of contents and indexes",
        "- Page numbers and headers/footers",
        "- Boilerplate text and legal disclaimers",
        "- Reference lists and bibliographies",
        "- Redundant whitespace sections",
        "",
        "### Section Extraction",
        "Extract these valuable sections:",
        "- Abstracts and executive summaries",
        "- Key conclusions and findings",
        "- Important definitions and concepts",
        "",
        "### Keywords",
        f"- Generate up to {max_keywords} meaningful keywords",
        "- Focus on main topics, concepts, and themes",
        "- Use lowercase unless proper nouns",
        "",
    ])
    
    # Category classification
    if categories:
        category_tree = _format_category_tree(categories)
        prompt_parts.extend([
            "### Category Classification",
            "Classify the document into this category hierarchy:",
            "```",
            category_tree,
            "```",
            "",
            "Return the category as a list from root to leaf, e.g., ['Technology', 'AI', 'Machine Learning']",
            "",
        ])
    else:
        prompt_parts.extend([
            "### Category Classification",
            "No category tree provided. Return an empty list for category.",
            "",
        ])
    
    # Finishing instructions
    prompt_parts.extend([
        "## Important",
        "",
        "- Work systematically through the document",
        "- You MUST call `finish_analysis` when done",
        "- Be thorough but efficient with tool calls",
        "- For `language`, use locale codes like 'en-US', 'zh-CN', 'ja-JP'",
    ])
    
    return "\n".join(prompt_parts)


def build_initial_user_message() -> str:
    """Build the initial user message to start analysis.
    
    Returns:
        The user message prompting analysis to begin.
    """
    return (
        "Please analyze this document. Start by reading the first section, "
        "then systematically work through it to clean, extract, and classify. "
        "Call finish_analysis when complete."
    )


def build_tool_error_message(tool_name: str, error: str) -> str:
    """Build an error message for a failed tool call.
    
    Args:
        tool_name: Name of the tool that failed.
        error: Error message from the failure.
        
    Returns:
        Formatted error message.
    """
    return f"Error executing {tool_name}: {error}. Please try a different approach."
