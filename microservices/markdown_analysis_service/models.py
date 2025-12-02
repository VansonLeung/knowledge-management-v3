"""Pydantic models for Markdown Analysis Service.

Defines request/response schemas and data transfer objects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# =============================================================================
# Category Models
# =============================================================================

class CategoryNode(BaseModel):
    """A hierarchical category with optional children."""
    
    name: str
    children: Optional[List[Union[str, "CategoryNode"]]] = None


# Enable recursive model references
CategoryNode.model_rebuild()

# Category can be a simple string or a nested CategoryNode
CategoryItem = Union[str, CategoryNode]


# =============================================================================
# Glossary Models
# =============================================================================

class GlossaryEntry(BaseModel):
    """A glossary term with definition and optional aliases."""
    
    term: str
    definition: str
    aliases: Optional[List[str]] = None


class GlossaryMatch(BaseModel):
    """A glossary term found in the analyzed text."""
    
    term: str
    definition: str
    occurrences: int = 1


# =============================================================================
# Section Models
# =============================================================================

class RemovedSection(BaseModel):
    """Record of lines removed during text cleaning."""
    
    start_line: int
    end_line: int
    reason: str
    content: str


class ExtractedSection(BaseModel):
    """A named section extracted from the document."""
    
    name: str
    start_line: int
    end_line: int
    text: str


# =============================================================================
# Request Models
# =============================================================================

class StudyTextRequest(BaseModel):
    """Request payload for text analysis."""
    
    # Required
    text: str = Field(
        ..., 
        description="The text or markdown content to analyze"
    )
    
    # Optional analysis inputs
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional metadata key-value pairs to provide context"
    )
    glossary: Optional[List[GlossaryEntry]] = Field(
        None, 
        description="Optional glossary of domain terms with definitions"
    )
    categories: Optional[List[CategoryItem]] = Field(
        None, 
        description="Optional category tree for classification"
    )
    max_keywords: Optional[int] = Field(
        None, 
        ge=1, 
        le=50,
        description="Maximum number of keywords to generate"
    )
    enable_polish_content: bool = Field(
        True,
        description="Enable the polish_and_add_content tool for cleaning messy text"
    )
    enable_glossary_lookup: bool = Field(
        True,
        description="Enable the lookup_glossary tool for term lookup"
    )
    is_standalone: bool = Field(
        False,
        description="Use standalone mode: chunks text and sends to LLM without iterative tool calling"
    )
    
    # LLM configuration overrides
    model: Optional[str] = Field(
        None, 
        description="Override the default LLM model"
    )
    api_key: Optional[str] = Field(
        None, 
        description="Override the default API key"
    )
    base_url: Optional[str] = Field(
        None, 
        description="Override the default API base URL"
    )


class EvaluateCleanlinessRequest(BaseModel):
    """Request payload for article cleanliness evaluation."""
    
    # Required
    text: str = Field(
        ..., 
        description="The text or markdown content to evaluate"
    )
    
    # LLM configuration overrides
    model: Optional[str] = Field(
        None, 
        description="Override the default LLM model"
    )
    api_key: Optional[str] = Field(
        None, 
        description="Override the default API key"
    )
    base_url: Optional[str] = Field(
        None, 
        description="Override the default API base URL"
    )


class EvaluateCleanlinessResponse(BaseModel):
    """Response payload for article cleanliness evaluation."""
    
    is_messy: bool = Field(
        ..., 
        description="Whether the article is messy and needs cleaning"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Explanation of why the article is clean or messy"
    )
    issues_found: Optional[List[str]] = Field(
        None,
        description="List of specific issues found in the text"
    )
    cleanliness_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Cleanliness score from 0 (very messy) to 100 (perfectly clean)"
    )
    model: Optional[str] = Field(
        None,
        description="The model used for evaluation"
    )
    total_chunks: Optional[int] = Field(
        None,
        description="Number of chunks the text was split into"
    )
    total_words: Optional[int] = Field(
        None,
        description="Total word count of the text"
    )


class PolishContentRequest(BaseModel):
    """Request payload for content polishing."""
    
    text: str = Field(
        ..., 
        description="The text or markdown content to polish"
    )
    
    # LLM configuration overrides
    model: Optional[str] = Field(
        None, 
        description="Override the default LLM model"
    )
    api_key: Optional[str] = Field(
        None, 
        description="Override the default API key"
    )
    base_url: Optional[str] = Field(
        None, 
        description="Override the default API base URL"
    )


class FinalizeContentRequest(BaseModel):
    """Request payload for content finalization (extract metadata)."""
    
    text: str = Field(
        ..., 
        description="The text or markdown content to finalize"
    )
    categories: Optional[List[CategoryItem]] = Field(
        None, 
        description="Optional category tree for classification"
    )
    max_keywords: Optional[int] = Field(
        10, 
        ge=1, 
        le=50,
        description="Maximum number of keywords to generate"
    )
    
    # LLM configuration overrides
    model: Optional[str] = Field(
        None, 
        description="Override the default LLM model"
    )
    api_key: Optional[str] = Field(
        None, 
        description="Override the default API key"
    )
    base_url: Optional[str] = Field(
        None, 
        description="Override the default API base URL"
    )


class GlossaryLookupRequest(BaseModel):
    """Request payload for glossary term lookup."""
    
    text: str = Field(
        ..., 
        description="The text to search for glossary terms"
    )
    glossary: List[GlossaryEntry] = Field(
        ..., 
        description="Glossary of domain terms with definitions"
    )
    
    # LLM configuration overrides
    model: Optional[str] = Field(
        None, 
        description="Override the default LLM model"
    )
    api_key: Optional[str] = Field(
        None, 
        description="Override the default API key"
    )
    base_url: Optional[str] = Field(
        None, 
        description="Override the default API base URL"
    )


# =============================================================================
# Response Models
# =============================================================================

class StudyTextResponse(BaseModel):
    """Response payload containing analysis results."""
    
    # Core analysis results
    language: str = Field(
        ..., 
        description="Detected language/locale (e.g., 'en-US', 'zh-CN')"
    )
    title: str = Field(
        ..., 
        description="Inferred or extracted document title"
    )
    content: str = Field(
        ..., 
        description="Cleaned text content after removing noise"
    )
    keywords: List[str] = Field(
        default_factory=list, 
        description="Generated keywords capturing main topics"
    )
    category: List[str] = Field(
        default_factory=list, 
        description="Hierarchical category path (e.g., ['Technology', 'AI'])"
    )
    
    # Detailed extraction results
    extracted_sections: List[ExtractedSection] = Field(
        default_factory=list,
        description="Named sections extracted from the document"
    )
    removed_sections: List[RemovedSection] = Field(
        default_factory=list,
        description="Sections removed during cleaning"
    )
    glossary_matches: List[GlossaryMatch] = Field(
        default_factory=list,
        description="Glossary terms found in the text"
    )
    
    # Metadata
    iterations_used: int = Field(
        0, 
        description="Number of LLM iterations used in analysis"
    )
