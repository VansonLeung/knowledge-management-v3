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
    enable_polish_content: bool = True,
    enable_glossary_lookup: bool = True,
) -> str:
    """Build the system prompt for document analysis (agentic mode).
    
    Args:
        total_lines: Total number of lines in the document.
        total_characters: Total number of characters in the document.
        has_glossary: Whether a glossary is available.
        categories: Optional category tree for classification.
        max_keywords: Maximum number of keywords to generate.
        enable_polish_content: Whether polish_and_add_content tool is available.
        enable_glossary_lookup: Whether lookup_glossary tool is available.
        
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
        "1. **Read** the document section by section using `read_text` (30-100 lines at a time)",
    ]
    
    next_step = 2
    
    # Add polish task if enabled
    if enable_polish_content:
        prompt_parts.extend([
            f"{next_step}. **Polish and add** meaningful content using `polish_and_add_content`",
            "   - For each section of main article content you find, provide a cleaned version",
            "   - Skip boilerplate, navigation, ads, and irrelevant content",
            "   - Fix formatting issues, HTML artifacts, and messy text",
            "   - Do NOT add new information or significantly rewrite",
            "   - DO NOT use this tool UNTIL YOU HAVE READ THE WHOLE DOCUMENT.",
            "   - DO NOT make up non-existing information.",
        ])
        next_step += 1
    
    # Glossary instruction
    if has_glossary and enable_glossary_lookup:
        prompt_parts.append(
            f"{next_step}. **Look up** technical terms in the glossary using `lookup_glossary`"
        )
        next_step += 1
    
    prompt_parts.append(
        f"{next_step}. **Finish** with language, title, keywords, and category using `finish_analysis`"
    )
    
    # Detailed guidelines
    prompt_parts.extend([
        "",
        "## Guidelines",
        "",
    ])
    
    if enable_polish_content:
        prompt_parts.extend([
            "### Content to SKIP (do not include in polished output)",
            "- Navigation menus and sidebars",
            "- Advertisements and promotional content",
            "- Cookie notices and legal disclaimers",
            "- Social media buttons and share links",
            "- Unrelated links and footer navigation",
            "- Page numbers and headers/footers",
            "",
            "### Content to POLISH and ADD (if some not found, omit)",
            "- Main article text and paragraphs",
            "- Article title and subtitles",
            "- Author information and publication date",
            "- Key conclusions and findings",
            "- Important definitions and concepts",
            "",
            "### Polishing Guidelines",
            "When using `polish_and_add_content`:",
            "- Remove HTML artifacts (e.g., &nbsp;, broken tags)",
            "- Fix obvious typos and formatting issues",
            "- Combine fragmented sentences if needed",
            "- Preserve markdown formatting (headers, lists, emphasis)",
            "- Keep all important information from the original",
            "- Do NOT add new information or significantly rewrite",
            "- Do NOT use the tool to add repetitive information across sections",
            "- DO NOT make up non-existing information.",
            "",
        ])
    
    prompt_parts.extend([
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


# =============================================================================
# Standalone Mode Prompts
# =============================================================================


def build_standalone_system_prompt(
    total_chunks: int,
    total_words: int,
    categories: Optional[List[CategoryItem]] = None,
    max_keywords: int = 10,
    enable_polish_content: bool = True,
) -> str:
    """Build the system prompt for standalone mode analysis.
    
    In standalone mode, the full document is provided in chunks via user messages.
    The LLM does not need to use read_text to navigate the document.
    
    Args:
        total_chunks: Number of text chunks provided.
        total_words: Approximate total word count.
        categories: Optional category tree for classification.
        max_keywords: Maximum number of keywords to generate.
        enable_polish_content: Whether polish_and_add_content tool is available.
        
    Returns:
        Complete system prompt string for standalone mode.
    """
    prompt_parts = [
        "You are a document analysis assistant. The full document has been provided to you in chunks.",
        "",
        f"The document is split into {total_chunks} chunk(s), approximately {total_words} words total.",
        "Chunks are separated by '...' to indicate the document continues.",
        "",
        "## Your Tasks",
        "",
    ]
    
    next_step = 1
    
    if enable_polish_content:
        prompt_parts.extend([
            f"{next_step}. **Read through all chunks** to understand the full document",
            f"{next_step + 1}. **Polish and add** meaningful content using `polish_and_add_content`",
            "   - For each meaningful section, provide a cleaned and polished version",
            "   - Skip boilerplate, navigation, ads, and irrelevant content",
            "   - Fix formatting issues, HTML artifacts, and messy text",
            "   - You may call this tool multiple times for different sections",
        ])
        next_step += 2
    else:
        prompt_parts.append(f"{next_step}. **Read through all chunks** to understand the full document")
        next_step += 1
    
    prompt_parts.append(
        f"{next_step}. **Finish** with language, title, keywords, and category using `finish_analysis`"
    )
    
    # Guidelines
    prompt_parts.extend([
        "",
        "## Guidelines",
        "",
    ])
    
    if enable_polish_content:
        prompt_parts.extend([
            "### Content to SKIP (do not include in polished output)",
            "- Navigation menus and sidebars",
            "- Advertisements and promotional content",
            "- Cookie notices and legal disclaimers",
            "- Social media buttons and share links",
            "- Unrelated links and footer navigation",
            "",
            "### Content to POLISH and ADD",
            "- Main article text and paragraphs",
            "- Article title and subtitles",
            "- Author information and publication date",
            "- Key conclusions and findings",
            "",
            "### Polishing Guidelines",
            "- Remove HTML artifacts (e.g., &nbsp;, broken tags)",
            "- Fix obvious typos and formatting issues",
            "- Preserve markdown formatting (headers, lists, emphasis)",
            "- Keep all important information from the original",
            "- Do NOT add new information or significantly rewrite",
            "",
        ])
    
    prompt_parts.extend([
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
            "Return the category as a list from root to leaf.",
            "",
        ])
    else:
        prompt_parts.extend([
            "### Category Classification",
            "No category tree provided. Return an empty list for category.",
            "",
        ])
    
    prompt_parts.extend([
        "## Important",
        "",
        "- You MUST call `finish_analysis` when done",
        "- For `language`, use locale codes like 'en-US', 'zh-CN', 'ja-JP'",
    ])
    
    return "\n".join(prompt_parts)


def build_standalone_final_message() -> str:
    """Build the final user message for standalone mode.
    
    Returns:
        User message prompting analysis completion.
    """
    return (
        "You have now seen the complete document. "
        "Please analyze it, polish the content if needed, and call finish_analysis with your findings."
    )


# =============================================================================
# Cleanliness Evaluation Prompts
# =============================================================================


def build_cleanliness_evaluation_prompt(
    total_chunks: int,
    total_words: int,
) -> str:
    """Build the system prompt for article cleanliness evaluation.
    
    Args:
        total_chunks: Number of text chunks provided.
        total_words: Approximate total word count.
        
    Returns:
        Complete system prompt string for cleanliness evaluation.
    """
    return f"""You are an article cleanliness evaluator. Your task is to determine whether a given text is "clean" (well-formatted, ready for consumption) or "messy" (contains artifacts, noise, or formatting issues that need cleaning).

The document is split into {total_chunks} chunk(s), approximately {total_words} words total.

## What makes an article MESSY:

1. **HTML/Web Artifacts**: Leftover HTML tags, &nbsp;, &amp;, broken tag fragments
2. **Navigation Noise**: Menu items, sidebar content, breadcrumbs mixed into main text
3. **Advertisement Remnants**: Ad text, promotional banners, "sponsored" content mixed in
4. **Formatting Issues**: 
   - Broken sentences split across lines incorrectly
   - Missing spaces between words
   - Inconsistent or broken markdown formatting
   - Page numbers or headers/footers mixed into content
5. **Encoding Issues**: Garbled characters, mojibake, incorrect unicode
6. **Extraction Artifacts**: 
   - Cookie notices, legal disclaimers interspersed with content
   - Social media share buttons text
   - "Read more" links scattered throughout
7. **OCR Artifacts**: If the text appears to be from OCR, look for typical OCR errors
8. **Duplicate Content**: Same paragraphs or sections repeated

## What makes an article CLEAN:

1. Well-structured paragraphs with proper spacing
2. Clear headings and sections (if applicable)
3. Consistent formatting throughout
4. No extraneous navigation or UI elements
5. Readable, flowing prose without artifacts
6. Proper markdown formatting (if markdown)

## Your Response:

Respond with a JSON object containing:

```json
{{
    "is_messy": true/false,
    "cleanliness_score": 0-100,
    "reasoning": "Brief explanation of your assessment",
    "issues_found": ["list", "of", "specific", "issues"] 
}}
```

- `is_messy`: true if the article needs cleaning, false if it's ready for use
- `cleanliness_score`: 0 = extremely messy, 100 = perfectly clean. Score below 70 typically indicates messy.
- `reasoning`: 1-2 sentences explaining your decision
- `issues_found`: Array of specific issues found (empty array if clean)

Be strict but fair. Minor formatting inconsistencies don't make an article messy. Focus on issues that would significantly impact readability or require cleanup before the content can be used."""


# =============================================================================
# Polish Content Prompts
# =============================================================================


def build_polish_content_prompt(
    total_chunks: int,
    total_words: int,
) -> str:
    """Build the system prompt for content polishing.
    
    Args:
        total_chunks: Number of text chunks provided.
        total_words: Approximate total word count.
        
    Returns:
        Complete system prompt string for content polishing.
    """
    return f"""You are a content polishing assistant. Your task is to clean and polish the given text while preserving its meaning and important information.

The document is split into {total_chunks} chunk(s), approximately {total_words} words total.

## Your Task:

Clean and polish the text by:

1. **Remove Web/HTML Artifacts**:
   - Remove leftover HTML tags, &nbsp;, &amp;, broken tag fragments
   - Remove navigation menus, sidebars, breadcrumbs
   - Remove advertisement text and promotional content
   - Remove cookie notices, legal disclaimers mixed into content
   - Remove social media buttons text, "Share on..." links
   - Remove page numbers, headers/footers

2. **Fix Formatting Issues**:
   - Fix broken sentences split incorrectly across lines
   - Add missing spaces between words
   - Fix inconsistent or broken markdown formatting
   - Combine fragmented paragraphs

3. **Preserve Important Content**:
   - Keep all main article text and paragraphs
   - Keep article title and subtitles
   - Keep author information and publication date
   - Keep key conclusions and findings
   - Preserve markdown formatting (headers, lists, emphasis)

## Important Guidelines:

- Do NOT add new information or significantly rewrite
- Do NOT summarize or shorten the content
- Do NOT make up information that isn't in the original
- Preserve the original structure and flow
- Keep all factual content intact

## Your Response:

Respond with a JSON object containing:

```json
{{
    "polished_content": "The cleaned and polished text...",
    "changes_made": ["list", "of", "changes", "made"],
    "sections_removed": ["list", "of", "removed", "sections"]
}}
```

- `polished_content`: The full polished text
- `changes_made`: Brief list of types of changes made
- `sections_removed`: Brief list of content types that were removed (e.g., "navigation menu", "cookie notice")"""


# =============================================================================
# Finalize Content Prompts
# =============================================================================


def build_finalize_content_prompt(
    total_chunks: int,
    total_words: int,
    categories: Optional[List[CategoryItem]] = None,
    max_keywords: int = 10,
) -> str:
    """Build the system prompt for content finalization.
    
    Args:
        total_chunks: Number of text chunks provided.
        total_words: Approximate total word count.
        categories: Optional category tree for classification.
        max_keywords: Maximum number of keywords to generate.
        
    Returns:
        Complete system prompt string for content finalization.
    """
    prompt_parts = [
        f"""You are a content analysis assistant. Your task is to extract metadata and classify the given text.

The document is split into {total_chunks} chunk(s), approximately {total_words} words total.

## Your Task:

Analyze the text and extract:

1. **Language**: Detect the primary language (use locale codes like 'en-US', 'zh-CN', 'ja-JP')

2. **Title**: Extract or infer the document title

3. **Summary**: Write a brief 1-2 sentence summary of the content

4. **Keywords**: Generate up to {max_keywords} meaningful keywords
   - Focus on main topics, concepts, and themes
   - Use lowercase unless proper nouns

5. **Author Information** (if available):
   - author: The author's name
   - published_by: Publisher or organization
   - published_at: Publication date

6. **Event Information** (if applicable):
   - date_start: Event start date
   - date_end: Event end date
   - date_duration: Duration description
   - location: Geographic location
   - venue: Specific venue name

7. **Related Entities**:
   - related_people: List of people mentioned
   - related_organizations: List of organizations mentioned
   - related_links: List of relevant URLs found""",
    ]
    
    # Category classification
    if categories:
        category_tree = _format_category_tree(categories)
        prompt_parts.append(f"""

8. **Category Classification**:
   Classify the document into this category hierarchy:
   ```
{category_tree}
   ```
   Return the category as a list from root to leaf, e.g., ['Technology', 'AI', 'Machine Learning']""")
    else:
        prompt_parts.append("""

8. **Category Classification**:
   No category tree provided. Return an empty list for category.""")
    
    prompt_parts.append("""

## Your Response:

Respond with a JSON object containing:

```json
{
    "language": "en-US",
    "title": "Document Title",
    "summary": "Brief summary of the content",
    "keywords": ["keyword1", "keyword2"],
    "category": ["Category", "Subcategory"],
    "author": "Author Name or null",
    "published_by": "Publisher or null",
    "published_at": "Date or null",
    "date_start": "Start date or null",
    "date_end": "End date or null",
    "date_duration": "Duration or null",
    "location": "Location or null",
    "venue": "Venue or null",
    "related_people": ["Person 1", "Person 2"],
    "related_organizations": ["Org 1", "Org 2"],
    "related_links": ["https://..."]
}
```

Only include fields that have actual values. Use null for fields with no information.""")
    
    return "\n".join(prompt_parts)


# =============================================================================
# Glossary Lookup Prompts
# =============================================================================


def build_glossary_lookup_prompt(
    total_chunks: int,
    total_words: int,
    glossary_terms: List[str],
) -> str:
    """Build the system prompt for glossary term lookup.
    
    Args:
        total_chunks: Number of text chunks provided.
        total_words: Approximate total word count.
        glossary_terms: List of glossary term names to search for.
        
    Returns:
        Complete system prompt string for glossary lookup.
    """
    terms_list = "\n".join(f"- {term}" for term in glossary_terms)
    
    return f"""You are a glossary matching assistant. Your task is to find occurrences of specific terms in the given text.

The document is split into {total_chunks} chunk(s), approximately {total_words} words total.

## Glossary Terms to Search For:

{terms_list}

## Your Task:

1. Search through the text for occurrences of each glossary term
2. Consider variations (singular/plural, case variations)
3. Consider aliases if the term appears differently in context
4. Count the approximate number of occurrences for each term found

## Your Response:

Respond with a JSON object containing:

```json
{{
    "matches": [
        {{
            "term": "Term Name",
            "occurrences": 3,
            "context_snippets": ["...snippet where term appears..."]
        }}
    ],
    "total_matches": 5
}}
```

- `matches`: Array of terms found in the text with occurrence counts
- `context_snippets`: 1-2 short snippets showing where the term appears (optional, max 100 chars each)
- `total_matches`: Total number of term occurrences found

Only include terms that actually appear in the text. Return empty matches array if no terms found."""
