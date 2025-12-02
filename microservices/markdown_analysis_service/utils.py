"""Utility functions for the Markdown Analysis Service.

Contains helper functions for text processing, chunking, and other utilities.
"""

from __future__ import annotations

from typing import List

import nltk
from nltk.tokenize import word_tokenize

# Ensure punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


def chunk_text_by_words(
    text: str,
    max_words: int = 1024,
    separator: str = "\n\n...\n\n",
) -> List[str]:
    """Split text into chunks with a maximum word count.
    
    Splits the text by words using NLTK tokenizer, ensuring each chunk 
    has at most `max_words` words.
    
    Args:
        text: The text to split into chunks.
        max_words: Maximum number of words per chunk (default: 1024).
        separator: Separator to add between chunks when they're displayed
                   together. Not added to the actual chunk content.
        
    Returns:
        List of text chunks, each with at most `max_words` words.
        
    Example:
        >>> text = "This is a sample text with many words."
        >>> chunks = chunk_text_by_words(text, max_words=3)
        >>> len(chunks)
        3
    """
    if not text or not text.strip():
        return []
    
    words = word_tokenize(text)
    
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    current_chunk_words = []
    
    for word in words:
        current_chunk_words.append(word)
        
        if len(current_chunk_words) >= max_words:
            chunks.append(" ".join(current_chunk_words))
            current_chunk_words = []
    
    # Add remaining words as the last chunk
    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))
    
    return chunks


def format_chunks_for_user_messages(
    chunks: List[str],
    separator: str = "\n\n...\n\n",
) -> List[str]:
    """Format chunks as user message content with continuation indicators.
    
    Adds chunk numbering and ellipsis separators to indicate the document
    continues across multiple chunks.
    
    Args:
        chunks: List of text chunks.
        separator: Separator to indicate continuation (default: ellipsis).
        
    Returns:
        List of formatted user message strings.
    """
    if not chunks:
        return []
    
    total_chunks = len(chunks)
    
    if total_chunks == 1:
        return [f"[Document - 1/1]\n\n{chunks[0]}"]
    
    formatted = []
    for i, chunk in enumerate(chunks):
        chunk_num = i + 1
        
        # Add header
        header = f"[Document Chunk {chunk_num}/{total_chunks}]"
        
        # Add continuation indicator
        if chunk_num < total_chunks:
            # Not the last chunk - add trailing ellipsis
            content = f"{header}\n\n{chunk}{separator}"
        else:
            # Last chunk - no trailing ellipsis
            content = f"{header}\n\n{chunk}"
        
        formatted.append(content)
    
    return formatted


def count_words(text: str) -> int:
    """Count the number of words in a text using NLTK tokenizer.
    
    Args:
        text: The text to count words in.
        
    Returns:
        Number of words in the text.
    """
    if not text or not text.strip():
        return 0
    return len(word_tokenize(text))
