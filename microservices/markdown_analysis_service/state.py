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
    
    Tracks polished content sections added by the LLM and provides methods
    for reading text and accumulating polished output.
    """
    
    def __init__(self, text: str) -> None:
        """Initialize with the original document text.
        
        Args:
            text: The full document text to analyze.
        """
        self._original_text = text
        self._lines = text.split("\n")
        self._characters = len(text)
        # Store polished content sections in order
        self._polished_sections: List[Dict[str, Any]] = []
    
    @property
    def total_lines(self) -> int:
        """Total number of lines in the document."""
        return len(self._lines)
    
    @property
    def total_characters(self) -> int:
        """Total number of characters in the document."""
        return self._characters
    
    @property
    def polished_sections(self) -> List[Dict[str, Any]]:
        """List of polished content sections."""
        return self._polished_sections
    
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
            Formatted string with line numbers and content.
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
        
        # Add polished sections count
        total_polished = len(self._polished_sections)
        total_chars_polished = sum(len(s["polished_text"]) for s in self._polished_sections)
        boundary_notes.append(f"[Polished sections: {total_polished}, Total chars: {total_chars_polished}]")
        
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
        """Get the concatenated polished content.
        
        Returns:
            All polished sections concatenated with double newlines.
        """
        if not self._polished_sections:
            return ""
        return "\n\n".join(s["polished_text"] for s in self._polished_sections)
    
    def add_polished_section(
        self,
        polished_text: str,
        start: Optional[int],
        end: Optional[int],
        section_label: Optional[str] = None,
    ) -> dict:
        """Add a polished section of content.
        
        Args:
            start: Starting line number (1-indexed).
            end: Ending line number (1-indexed, inclusive).
            polished_text: The polished/cleaned version of the text.
            section_label: Optional label for this section.
            
        Returns:
            Dict with section summary.
        """
        section = {
            "start_line": start,
            "end_line": end,
            "polished_text": polished_text,
            "section_label": section_label,
            "original_char_count": sum(
                len(self._lines[i])
                for i in range(max(0, start - 1), min(len(self._lines), end))
            ),
            "polished_char_count": len(polished_text),
        }
        
        self._polished_sections.append(section)
        
        # Calculate totals
        total_polished_chars = sum(len(s["polished_text"]) for s in self._polished_sections)
        
        return {
            "section_number": len(self._polished_sections),
            "start_line": start,
            "end_line": end,
            "section_label": section_label,
            "polished_char_count": len(polished_text),
            "total_sections": len(self._polished_sections),
            "total_polished_chars": total_polished_chars,
            "polished_preview": polished_text[:200] + ("..." if len(polished_text) > 200 else ""),
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
        """Polished content sections (for backward compatibility)."""
        return self._document.polished_sections
    
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
    def related_people(self) -> Optional[List[str]]:
        """Related people (if applicable)."""
        return getattr(self, "_related_people", None)
    
    @property
    def related_organizations(self) -> Optional[List[str]]:
        """Related organizations (if applicable)."""
        return getattr(self, "_related_organizations", None)
    
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
    
    def polish_and_add_content(
        self,
        polished_text: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        section_label: Optional[str] = None,
    ) -> str:
        """Add a polished section of content to the final output.
        
        Args:
            start: Starting line number of original content (1-indexed).
            end: Ending line number of original content (1-indexed, inclusive).
            polished_text: The cleaned and polished version of the text.
            section_label: Optional label for this content section.
            
        Returns:
            Confirmation message with section summary.
        """
        result = self._document.add_polished_section(
            start=start,
            end=end,
            polished_text=polished_text,
            section_label=section_label,
        )
        
        # Format result message
        label_note = f"Section label: {result['section_label']}\n" if result['section_label'] else ""
        
        return (
            f"=== POLISHED CONTENT ADDED ===\n"
            f"Section #{result['section_number']} (from lines {start}-{end})\n"
            f"{label_note}"
            f"\n"
            f"SECTION SUMMARY:\n"
            f"  - Polished text: {result['polished_char_count']} characters\n"
            f"  - Total sections so far: {result['total_sections']}\n"
            f"  - Total polished content: {result['total_polished_chars']} characters\n"
            f"\n"
            f"Content preview: {result['polished_preview']}"
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
        related_people: Optional[List[str]] = None,
        related_organizations: Optional[List[str]] = None,
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
            related_people: Related people related to the main article.
            related_organizations: Related organizations related to the main article.
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
        self._related_people = related_people
        self._related_organizations = related_organizations
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
        # Format polished sections for response
        polished_sections = [
            {
                "section_number": i + 1,
                "start_line": s["start_line"],
                "end_line": s["end_line"],
                "section_label": s.get("section_label"),
                "polished_char_count": s["polished_char_count"],
            }
            for i, s in enumerate(self.classifications)
        ]
        
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
            "related_people": self.related_people,
            "related_organizations": self.related_organizations,
            "related_links": self.related_links,
            "content": self.cleaned_content,
            "polished_sections": polished_sections,
            "glossary_matches": [m.model_dump() for m in self.glossary_matches],
            "iterations_used": iterations_used,
        }
