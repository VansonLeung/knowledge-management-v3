"""Analysis state management for document processing.

Manages the mutable state during text analysis including:
- Line classification as content
- Glossary matching
- Final results accumulation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models import (
    CategoryItem,
    GlossaryEntry,
    GlossaryMatch,
)


class DocumentState:
    """Manages document content with line-level operations.
    
    Tracks which lines are classified as content and provides methods
    for reading and classifying sections.
    """
    
    def __init__(self, text: str) -> None:
        """Initialize with the original document text.
        
        Args:
            text: The full document text to analyze.
        """
        self._original_text = text
        self._lines = text.split("\n")
        self._characters = len(text)
        # Track which lines are classified as content (False = not classified yet)
        self._content_mask = [False] * len(self._lines)
    
    @property
    def total_lines(self) -> int:
        """Total number of lines in the document."""
        return len(self._lines)
    
    @property
    def total_characters(self) -> int:
        """Total number of characters in the document."""
        return self._characters
    
    def get_lines_with_numbers(
        self,
        start: int,
        end: int,
        context: int = 3,
    ) -> str:
        """Get lines with line numbers and context.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            context: Number of context lines before and after.
            
        Returns:
            Formatted string with line numbers and status prefixes:
            - "  " for unclassified lines
            - "> " for lines in the requested range
            - "✓ " for lines already classified as content
        """
        total_lines = len(self._lines)
        
        # Check if request is entirely beyond document
        if start > total_lines:
            return (
                f"[END OF DOCUMENT] No content at lines {start}-{end}. "
                f"Document has {total_lines} lines total. "
                f"You have reached the end of the document."
            )
        
        # Clamp end to document bounds
        actual_end = min(end, total_lines)
        
        start_idx = max(0, start - 1 - context)
        end_idx = min(total_lines, actual_end + context)
        
        result = []
        for i in range(start_idx, end_idx):
            result.append(f"{self._lines[i]}")
        
        output = "\n".join(result)
        
        # Add boundary indicators
        boundary_notes = []
        if start == 1:
            boundary_notes.append("[START OF DOCUMENT]")
        if actual_end >= total_lines:
            boundary_notes.append(f"[END OF DOCUMENT - line {total_lines} is the last line]")
        if end > total_lines:
            boundary_notes.append(f"(requested up to line {end}, but document only has {total_lines} lines)")
        
        # Add classification status
        total_classified = sum(self._content_mask)
        boundary_notes.append(f"[Content classified: {total_classified}/{total_lines} lines]")
        
        if boundary_notes:
            output = "\n".join(boundary_notes) + "\n\n" + output
        
        return output
    
    def get_section_text(
        self,
        start: int,
        end: int,
    ) -> tuple:
        """Get text for a section.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            
        Returns:
            Tuple of (section_text, was_truncated).
        """
        start_idx = max(0, start - 1)
        end_idx = min(len(self._lines), end)
        
        section_lines = self._lines[start_idx:end_idx]
        
        text = "\n".join(section_lines)
        
        # Apply word limit
        truncated, was_truncated = self._truncate_by_words(text)
        return truncated, was_truncated
    
    def get_cleaned_text(self) -> str:
        """Get only the lines classified as content.
        
        Returns:
            The document text with only classified content lines.
        """
        return "\n".join(
            line
            for i, line in enumerate(self._lines)
            if self._content_mask[i]
        )
    
    def classify_lines(self, start: int, end: int) -> dict:
        """Classify a range of lines as content.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            
        Returns:
            Dict with classification summary.
        """
        start_idx = max(0, start - 1)
        end_idx = min(len(self._lines), end)
        
        # Count how many lines are newly classified
        newly_classified = 0
        already_classified = 0
        
        for i in range(start_idx, end_idx):
            if self._content_mask[i]:
                already_classified += 1
            else:
                self._content_mask[i] = True
                newly_classified += 1
        
        # Get preview of classified content
        classified_content = "\n".join(self._lines[start_idx:end_idx])
        
        # Count total classified lines
        total_classified = sum(self._content_mask)
        
        return {
            "start_line": start,
            "end_line": end,
            "newly_classified": newly_classified,
            "already_classified": already_classified,
            "total_classified_lines": total_classified,
            "total_lines": len(self._lines),
            "content_preview": classified_content[:300] + ("..." if len(classified_content) > 300 else ""),
        }


class GlossaryState:
    """Manages glossary lookup and match tracking."""
    
    def __init__(self, entries: Optional[List[GlossaryEntry]] = None) -> None:
        """Initialize with optional glossary entries.
        
        Args:
            entries: List of glossary entries to use for lookups.
        """
        self._entries = entries or []
        self._matches: Dict[str, GlossaryMatch] = {}
    
    @property
    def entries(self) -> List[GlossaryEntry]:
        """The glossary entries available for lookup."""
        return self._entries
    
    @property
    def matches(self) -> List[GlossaryMatch]:
        """List of matched glossary terms."""
        return list(self._matches.values())
    
    def lookup(self, terms: List[str]) -> str:
        """Look up terms in the glossary.
        
        Args:
            terms: List of terms to search for.
            
        Returns:
            Formatted string with lookup results.
        """
        results = []
        
        for term in terms:
            term_lower = term.lower()
            found = False
            
            for entry in self._entries:
                # Check main term and aliases
                is_match = entry.term.lower() == term_lower
                if entry.aliases:
                    is_match = is_match or any(
                        alias.lower() == term_lower
                        for alias in entry.aliases
                    )
                
                if is_match:
                    # Track or increment match
                    if entry.term not in self._matches:
                        self._matches[entry.term] = GlossaryMatch(
                            term=entry.term,
                            definition=entry.definition,
                            occurrences=1,
                        )
                    else:
                        self._matches[entry.term].occurrences += 1
                    
                    results.append(f"- {entry.term}: {entry.definition}")
                    found = True
                    break
            
            if not found:
                results.append(f"- {term}: (not found in glossary)")
        
        return "\n".join(results) if results else "No terms found in glossary."


class AnalysisState:
    """Complete analysis state for a document.
    
    Aggregates document state, glossary state, section tracking,
    and final analysis results.
    """
    
    def __init__(
        self,
        text: str,
        glossary: Optional[List[GlossaryEntry]] = None,
        categories: Optional[List[CategoryItem]] = None,
        max_keywords: int = 10,
    ) -> None:
        """Initialize analysis state.
        
        Args:
            text: The document text to analyze.
            glossary: Optional glossary entries.
            categories: Optional category tree for classification.
            max_keywords: Maximum keywords to generate.
        """
        self._document = DocumentState(text)
        self._glossary = GlossaryState(glossary)
        self._categories = categories
        self._max_keywords = max_keywords
        
        # Content classification tracking
        self._classifications: List[Dict[str, Any]] = []
        
        # Final results
        self._language: Optional[str] = None
        self._title: Optional[str] = None
        self._keywords: List[str] = []
        self._category: List[str] = []
        self._is_finished = False
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def total_lines(self) -> int:
        """Total number of lines in the document."""
        return self._document.total_lines
    
    @property
    def total_characters(self) -> int:
        """Total number of characters in the document."""
        return self._document.total_characters
    
    @property
    def categories(self) -> Optional[List[CategoryItem]]:
        """The category tree for classification."""
        return self._categories
    
    @property
    def glossary_entries(self) -> List[GlossaryEntry]:
        """Available glossary entries."""
        return self._glossary.entries
    
    @property
    def max_keywords(self) -> int:
        """Maximum number of keywords to generate."""
        return self._max_keywords
    
    @property
    def is_finished(self) -> bool:
        """Whether analysis has been completed."""
        return self._is_finished
    
    @property
    def classifications(self) -> List[Dict[str, Any]]:
        """Content classification history."""
        return self._classifications
    
    @property
    def glossary_matches(self) -> List[GlossaryMatch]:
        """Glossary terms that were matched."""
        return self._glossary.matches
    
    # -------------------------------------------------------------------------
    # Result Properties
    # -------------------------------------------------------------------------
    
    @property
    def language(self) -> str:
        """Detected language (or 'unknown')."""
        return self._language or "unknown"
    
    @property
    def title(self) -> str:
        """Document title (or 'Untitled')."""
        return self._title or "Untitled"
    
    @property
    def keywords(self) -> List[str]:
        """Generated keywords."""
        return self._keywords
    
    @property
    def category(self) -> List[str]:
        """Hierarchical category path."""
        return self._category
    
    @property
    def cleaned_content(self) -> str:
        """Document content with removed lines filtered out."""
        return self._document.get_cleaned_text()
    
    @property
    def summary(self) -> str:
        """Document summary (if available)."""
        return getattr(self, "_summary", "")
    
    @property
    def author(self) -> Optional[str]:
        """Document author (if applicable)."""
        return getattr(self, "_author", None)
    
    @property
    def published_by(self) -> Optional[str]:
        """Publisher (if applicable)."""
        return getattr(self, "_published_by", None)
    
    @property
    def published_at(self) -> Optional[str]:
        """Publication date (if applicable)."""
        return getattr(self, "_published_at", None)
    
    @property
    def date_start(self) -> Optional[str]:
        """Event start date (if applicable)."""
        return getattr(self, "_date_start", None)

    @property
    def date_end(self) -> Optional[str]:
        """Event end date (if applicable)."""
        return getattr(self, "_date_end", None)
    
    @property
    def date_duration(self) -> Optional[str]:
        """Event duration (if applicable)."""
        return getattr(self, "_date_duration", None)
    
    @property
    def location(self) -> Optional[str]:
        """Event location (if applicable)."""
        return getattr(self, "_location", None)
    
    @property
    def venue(self) -> Optional[str]:
        """Event venue (if applicable)."""
        return getattr(self, "_venue", None)
    
    @property
    def related_links(self) -> Optional[List[str]]:
        """Related links (if applicable)."""
        return getattr(self, "_related_links", None)
    
    # -------------------------------------------------------------------------
    # Tool Operations
    # -------------------------------------------------------------------------
    
    def read_lines(
        self,
        start: int,
        end: int,
        context: int = 3,
    ) -> str:
        """Read lines with numbers and context.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            context: Number of context lines.
            
        Returns:
            Formatted line-numbered text.
        """
        return self._document.get_lines_with_numbers(
            start, end, context,
        )
    
    def extract_lines_as_main_article(
        self,
        start: int,
        end: int,
        label: str = "",
    ) -> str:
        """Extract a range of lines as meaningful content.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            label: Optional label for this content section.
            
        Returns:
            Confirmation message with classification summary.
        """
        result = self._document.classify_lines(start, end)
        
        # Track the classification
        self._classifications.append({
            "start_line": start,
            "end_line": end,
            "line_count": result["newly_classified"] + result["already_classified"],
        })
        
        # Format result message
        label_note = f"Label: {label}\n" if label else ""
        
        return (
            f"=== LINES CLASSIFIED AS CONTENT ===\n"
            f"{label_note}"
            f"Lines {start}-{end} marked as content.\n"
            f"\n"
            f"CLASSIFICATION SUMMARY:\n"
            f"  - Newly classified: {result['newly_classified']} lines\n"
            f"  - Already classified: {result['already_classified']} lines\n"
            f"  - Total classified so far: {result['total_classified_lines']} / {result['total_lines']} lines\n"
            f"\n"
            f"Content preview: {result['content_preview']}"
        )
    
    def lookup_glossary(self, terms: List[str]) -> str:
        """Look up terms in the glossary.
        
        Args:
            terms: Terms to look up.
            
        Returns:
            Lookup results.
        """
        return self._glossary.lookup(terms)
    
    def finish(
        self,
        language: str,
        title: str,
        summary: str,
        keywords: List[str],
        category: List[str],
        author: Optional[str] = None,
        published_by: Optional[str] = None,
        published_at: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        date_duration: Optional[str] = None,
        location: Optional[str] = None,
        venue: Optional[str] = None,
        related_links: Optional[List[str]] = None,
    ) -> str:
        """Complete the analysis with final results.
        
        Args:
            language: Detected language/locale.
            title: Document title.
            summary: Document summary.
            keywords: Generated keywords.
            category: Category path.
            author: Document author.
            published_by: Publisher.
            published_at: Publication date.
            date_start: Event start date.
            date_end: Event end date.
            date_duration: Event duration.
            location: Event location.
            venue: Event venue.
            related_links: Related links.
        Returns:
            Confirmation message.
        """
        self._language = language
        self._title = title
        self._summary = summary
        self._keywords = keywords[:self._max_keywords]
        self._category = category
        self._author = author
        self._published_by = published_by
        self._published_at = published_at
        self._date_start = date_start
        self._date_end = date_end
        self._date_duration = date_duration
        self._location = location
        self._venue = venue
        self._related_links = related_links
        self._is_finished = True
        
        return "Analysis complete."
    
    # -------------------------------------------------------------------------
    # Result Building
    # -------------------------------------------------------------------------
    
    def to_response_dict(self, iterations_used: int) -> Dict[str, Any]:
        """Convert state to response dictionary.
        
        Args:
            iterations_used: Number of LLM iterations used.
            
        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "language": self.language,
            "title": self.title,
            "keywords": self.keywords,
            "category": self.category,
            "summary": self.summary,
            "author": self.author,
            "published_by": self.published_by,
            "published_at": self.published_at,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "date_duration": self.date_duration,
            "location": self.location,
            "venue": self.venue,
            "related_links": self.related_links,
            "content": self.cleaned_content,
            "classifications": self._classifications,
            "glossary_matches": [m.model_dump() for m in self.glossary_matches],
            "iterations_used": iterations_used,
        }
