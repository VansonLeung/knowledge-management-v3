"""Analysis engine with SSE streaming support.

Handles the main analysis loop, tool execution, and SSE event generation.
"""

from __future__ import annotations

import json
import traceback
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from config import ServiceConfig
from models import (
    CategoryItem,
    GlossaryEntry,
    StudyTextRequest,
    EvaluateCleanlinessRequest,
    PolishContentRequest,
    FinalizeContentRequest,
    GlossaryLookupRequest,
)
from prompts import (
    build_initial_user_message,
    build_system_prompt,
    build_tool_error_message,
    build_standalone_system_prompt,
    build_standalone_final_message,
    build_cleanliness_evaluation_prompt,
    build_polish_content_prompt,
    build_finalize_content_prompt,
    build_glossary_lookup_prompt,
)
from state import AnalysisState
from tools import get_tool_definitions, get_standalone_tools
from utils import chunk_text_by_words, format_chunks_for_user_messages, count_words


# -----------------------------------------------------------------------------
# Config Resolution Helper
# -----------------------------------------------------------------------------


def resolve_config(
    request: StudyTextRequest,
    serviceConfig: ServiceConfig,
) -> tuple[str, str, str]:
    """Resolve effective model, api_key, and base_url from request overrides.
    
    Args:
        request: The analysis request with optional overrides.
        serviceConfig: Default service configuration.
        
    Returns:
        Tuple of (model, api_key, base_url) with request overrides applied.
    """
    model = request.model if request.model else serviceConfig.model
    api_key = request.api_key if request.api_key else serviceConfig.api_key
    base_url = request.base_url if request.base_url else serviceConfig.base_url
    return model, api_key, base_url


# -----------------------------------------------------------------------------
# SSE Event Formatting
# -----------------------------------------------------------------------------


def sse_event(event: str, data: Any) -> str:
    """Format a Server-Sent Event.
    
    Args:
        event: Event type name.
        data: Event payload (will be JSON serialized).
        
    Returns:
        Formatted SSE string with event type and data.
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_data}\n\n"


# -----------------------------------------------------------------------------
# Tool Execution
# -----------------------------------------------------------------------------


def execute_tool(
    state: AnalysisState,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """Execute a tool call and return the result.
    
    Args:
        state: Current analysis state.
        tool_name: Name of the tool to execute.
        arguments: Tool arguments.
        
    Returns:
        Tool execution result as a string.
        
    Raises:
        ValueError: If tool name is unknown.
    """
    if tool_name == "read_text":
        return state.read_lines(
            start=arguments["start_line"],
            end=arguments["end_line"],
            context=arguments.get("context", 3),
        )
    
    elif tool_name == "polish_and_add_content":
        return state.polish_and_add_content(
            polished_text=arguments["polished_text"],
            start=arguments["start_line"],
            end=arguments["end_line"],
            section_label=arguments.get("section_label"),
        )
    
    elif tool_name == "lookup_glossary":
        return state.lookup_glossary(
            terms=arguments["terms"],
        )
    
    elif tool_name == "finish_analysis":
        return state.finish(
            language=arguments["language"],
            title=arguments["title"],
            summary=arguments.get("summary"),
            keywords=arguments["keywords"],
            category=arguments.get("category", []),
            author=arguments.get("author"),
            published_by=arguments.get("published_by"),
            published_at=arguments.get("published_at"),
            date_start=arguments.get("date_start"),
            date_end=arguments.get("date_end"),
            date_duration=arguments.get("date_duration"),
            location=arguments.get("location"),
            venue=arguments.get("venue"),
            related_people=arguments.get("related_people", []),
            related_organizations=arguments.get("related_organizations", []),
            related_links=arguments.get("related_links", []),
        )
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# -----------------------------------------------------------------------------
# Analysis Engine - Agentic Mode
# -----------------------------------------------------------------------------


async def analyze_document_stream(
    request: StudyTextRequest,
    serviceConfig: ServiceConfig,
) -> AsyncGenerator[str, None]:
    """Analyze a document with SSE streaming.
    
    Dispatches to either agentic or standalone mode based on request.is_standalone.
    
    Args:
        request: The analysis request.
        serviceConfig: Application serviceConfig.
        
    Yields:
        SSE formatted event strings.
    """
    if request.is_standalone:
        async for event in analyze_document_standalone_stream(request, serviceConfig):
            yield event
    else:
        async for event in analyze_document_agentic_stream(request, serviceConfig):
            yield event


async def analyze_document_agentic_stream(
    request: StudyTextRequest,
    serviceConfig: ServiceConfig,
) -> AsyncGenerator[str, None]:
    """Analyze a document with SSE streaming (agentic mode).
    
    Performs iterative LLM analysis with tool calling, streaming
    progress updates via Server-Sent Events.
    
    Args:
        request: The analysis request.
        serviceConfig: Application serviceConfig.
        
    Yields:
        SSE formatted event strings.
    """
    # Resolve effective config (apply request overrides)
    model, api_key, base_url = resolve_config(request, serviceConfig)
    
    # Create state first so we can get total_lines
    state = AnalysisState(
        text=request.text,
        glossary=request.glossary,
        categories=request.categories,
        max_keywords=request.max_keywords if request.max_keywords else serviceConfig.max_keywords,
    )
    
    # Send start event
    yield sse_event("start", {
        "message": "Starting document analysis",
        "total_lines": state.total_lines,
        "total_characters": state.total_characters,
        "model": model,
        "max_iterations": serviceConfig.max_iterations,
    })
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Check if polish content is enabled
    enable_polish_content = request.enable_polish_content
    enable_glossary_lookup = request.enable_glossary_lookup
    
    # Build system prompt
    system_prompt = build_system_prompt(
        total_lines=state.total_lines,
        total_characters=state.total_characters,
        has_glossary=len(state.glossary_entries) > 0,
        categories=state.categories,
        max_keywords=state.max_keywords,
        enable_polish_content=enable_polish_content,
        enable_glossary_lookup=enable_glossary_lookup,
    )
    
    # Initialize messages
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_initial_user_message()},
    ]
    
    # Get tool definitions
    tools = get_tool_definitions(enable_polish_content, enable_glossary_lookup)
    
    # Analysis loop
    iteration = 0
    
    while not state.is_finished and iteration < serviceConfig.max_iterations:
        iteration += 1
        
        yield sse_event("iteration", {
            "iteration": iteration,
            "max_iterations": serviceConfig.max_iterations,
        })
        
        try:
            # Call LLM with streaming
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
            )
            
            # Accumulate response
            assistant_content = ""
            tool_calls_data: Dict[int, Dict[str, Any]] = {}
            
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                
                if not delta:
                    continue
                
                # Handle content chunks
                if delta.content:
                    assistant_content += delta.content
                    yield sse_event("chunk", {"content": delta.content})
                
                # Handle tool call chunks
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments
            
            # Process tool calls
            tool_calls = list(tool_calls_data.values()) if tool_calls_data else []
            
            if tool_calls:
                # Append assistant message with tool calls
                # OpenAI API requires content to be string, not None
                messages.append({
                    "role": "assistant",
                    "content": assistant_content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls
                    ],
                })
                
                # Execute each tool call
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_id = tc["id"]
                    
                    try:
                        parsed_args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        parsed_args = {}
                    
                    yield sse_event("tool_call", {
                        "name": tool_name,
                        "id": tool_id,
                        "arguments": parsed_args,
                    })
                    
                    try:
                        result = execute_tool(state, tool_name, parsed_args)
                    except Exception as e:
                        result = build_tool_error_message(tool_name, str(e))
                    
                    yield sse_event("tool_result", {
                        "name": tool_name,
                        "id": tool_id,
                        "result": result[:500] if len(result) > 500 else result,
                    })
                    
                    # Append tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result,
                    })
            
            else:
                # No tool calls - append as regular assistant message
                if assistant_content:
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                    })
        
        except Exception as e:
            yield sse_event("error", {
                "message": f"LLM error: {str(e)}",
                "traceback": traceback.format_exc(),
            })
            break
    
    # Final result
    if state.is_finished:
        yield sse_event("complete", state.to_response_dict(iteration))
    else:
        # Timed out or errored - return partial results
        yield sse_event("complete", {
            **state.to_response_dict(iteration),
            "warning": f"Analysis incomplete after {iteration} iterations",
        })


# -----------------------------------------------------------------------------
# Analysis Engine - Standalone Mode
# -----------------------------------------------------------------------------


async def analyze_document_standalone_stream(
    request: StudyTextRequest,
    serviceConfig: ServiceConfig,
) -> AsyncGenerator[str, None]:
    """Analyze a document with SSE streaming (standalone mode).
    
    In standalone mode:
    - Text is chunked into ≤1024 words each
    - Chunks are provided as user messages
    - LLM processes all chunks and calls tools without iterative reading
    
    Args:
        request: The analysis request.
        serviceConfig: Application serviceConfig.
        
    Yields:
        SSE formatted event strings.
    """
    # Resolve effective config (apply request overrides)
    model, api_key, base_url = resolve_config(request, serviceConfig)
    
    # Chunk the text
    chunks = chunk_text_by_words(request.text, max_words=1024)
    total_words = count_words(request.text)
    formatted_chunks = format_chunks_for_user_messages(chunks)
    
    # Create state
    state = AnalysisState(
        text=request.text,
        glossary=request.glossary,
        categories=request.categories,
        max_keywords=request.max_keywords if request.max_keywords else serviceConfig.max_keywords,
    )
    
    # Send start event
    yield sse_event("start", {
        "message": "Starting standalone document analysis",
        "mode": "standalone",
        "total_chunks": len(chunks),
        "total_words": total_words,
        "total_lines": state.total_lines,
        "total_characters": state.total_characters,
        "model": model,
        "max_iterations": serviceConfig.max_iterations,
    })
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Check if polish content is enabled
    enable_polish_content = request.enable_polish_content
    
    # Build system prompt for standalone mode
    system_prompt = build_standalone_system_prompt(
        total_chunks=len(chunks),
        total_words=total_words,
        categories=state.categories,
        max_keywords=state.max_keywords,
        enable_polish_content=enable_polish_content,
    )
    
    # Build messages: system + chunk messages + final instruction
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add each chunk as a user message
    for chunk_content in formatted_chunks:
        messages.append({"role": "user", "content": chunk_content})
    
    # Add final instruction message
    messages.append({"role": "user", "content": build_standalone_final_message()})
    
    # Get standalone tools
    tools = get_standalone_tools(enable_polish_content)
    
    # Analysis loop (may need multiple iterations for tool calls)
    iteration = 0
    
    while not state.is_finished and iteration < serviceConfig.max_iterations:
        iteration += 1
        
        yield sse_event("iteration", {
            "iteration": iteration,
            "max_iterations": serviceConfig.max_iterations,
            "mode": "standalone",
        })
        
        try:
            # Call LLM with streaming
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
            )
            
            # Accumulate response
            assistant_content = ""
            tool_calls_data: Dict[int, Dict[str, Any]] = {}
            
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                
                if not delta:
                    continue
                
                # Handle content chunks
                if delta.content:
                    assistant_content += delta.content
                    yield sse_event("chunk", {"content": delta.content})
                
                # Handle tool call chunks
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments
            
            # Process tool calls
            tool_calls = list(tool_calls_data.values()) if tool_calls_data else []
            
            if tool_calls:
                # Append assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": assistant_content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls
                    ],
                })
                
                # Execute each tool call
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_id = tc["id"]
                    
                    try:
                        parsed_args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        parsed_args = {}
                    
                    yield sse_event("tool_call", {
                        "name": tool_name,
                        "id": tool_id,
                        "arguments": parsed_args,
                    })
                    
                    try:
                        result = execute_tool(state, tool_name, parsed_args)
                    except Exception as e:
                        result = build_tool_error_message(tool_name, str(e))
                    
                    yield sse_event("tool_result", {
                        "name": tool_name,
                        "id": tool_id,
                        "result": result[:500] if len(result) > 500 else result,
                    })
                    
                    # Append tool result message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result,
                    })
            
            else:
                # No tool calls - append as regular assistant message
                if assistant_content:
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                    })
        
        except Exception as e:
            yield sse_event("error", {
                "message": f"LLM error: {str(e)}",
                "traceback": traceback.format_exc(),
            })
            break
    
    # Final result
    if state.is_finished:
        yield sse_event("complete", {
            **state.to_response_dict(iteration),
            "mode": "standalone",
            "chunks_processed": len(chunks),
        })
    else:
        # Timed out or errored - return partial results
        yield sse_event("complete", {
            **state.to_response_dict(iteration),
            "mode": "standalone",
            "chunks_processed": len(chunks),
            "warning": f"Analysis incomplete after {iteration} iterations",
        })


# -----------------------------------------------------------------------------
# Cleanliness Evaluation
# -----------------------------------------------------------------------------


async def evaluate_article_cleanliness(
    request: EvaluateCleanlinessRequest,
    serviceConfig: ServiceConfig,
) -> Dict[str, Any]:
    """Evaluate whether an article's text is clean or messy.
    
    Chunks the text and prompts LLM to evaluate cleanliness.
    
    Args:
        request: The evaluation request with text and optional config overrides.
        serviceConfig: Default service configuration.
        
    Returns:
        Dictionary with is_messy boolean and details.
    """
    # Resolve effective config
    model = request.model if request.model else serviceConfig.model
    api_key = request.api_key if request.api_key else serviceConfig.api_key
    base_url = request.base_url if request.base_url else serviceConfig.base_url
    
    # Chunk the text
    chunks = chunk_text_by_words(request.text, max_words=1024)
    total_words = count_words(request.text)
    formatted_chunks = format_chunks_for_user_messages(chunks)
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Build messages
    system_prompt = build_cleanliness_evaluation_prompt(
        total_chunks=len(chunks),
        total_words=total_words,
    )
    
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add each chunk as a user message
    for chunk_content in formatted_chunks:
        messages.append({"role": "user", "content": chunk_content})
    
    # Add final instruction
    messages.append({
        "role": "user",
        "content": "Please evaluate this article's cleanliness and respond with ONLY the JSON object, no other text."
    })
    
    try:
        # Call LLM (non-streaming for simplicity)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        
        content = response.choices[0].message.content or "{}"
        
        # Try to extract JSON from the response
        # The LLM might wrap JSON in markdown code blocks
        json_content = content.strip()
        
        # Remove markdown code block if present
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        elif json_content.startswith("```"):
            json_content = json_content[3:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        json_content = json_content.strip()
        
        # Try to find JSON object in the response
        if not json_content.startswith("{"):
            # Look for JSON object in the text
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
        
        # Parse JSON response
        try:
            result = json.loads(json_content)
        except json.JSONDecodeError:
            result = {
                "is_messy": False,
                "reasoning": "Failed to parse LLM response as JSON",
                "raw_response": content[:500],
            }
        
        # Ensure is_messy is a boolean
        if "is_messy" not in result:
            result["is_messy"] = False
        else:
            result["is_messy"] = bool(result["is_messy"])
        
        # Add metadata
        result["model"] = model
        result["total_chunks"] = len(chunks)
        result["total_words"] = total_words
        
        return result
        
    except Exception as e:
        return {
            "is_messy": False,
            "error": str(e),
            "model": model,
            "total_chunks": len(chunks),
            "total_words": total_words,
        }


# -----------------------------------------------------------------------------
# Helper: Extract JSON from LLM Response
# -----------------------------------------------------------------------------


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """Extract JSON from an LLM response that may contain markdown formatting.
    
    Args:
        content: Raw LLM response content.
        
    Returns:
        Parsed JSON as dictionary, or dict with error info if parsing fails.
    """
    import re
    
    json_content = content.strip()
    
    # Remove markdown code block if present
    if json_content.startswith("```json"):
        json_content = json_content[7:]
    elif json_content.startswith("```"):
        json_content = json_content[3:]
    if json_content.endswith("```"):
        json_content = json_content[:-3]
    json_content = json_content.strip()
    
    # Try to find JSON object in the response
    if not json_content.startswith("{"):
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
    
    try:
        return json.loads(json_content)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse LLM response as JSON",
            "raw_response": content[:500],
        }


# -----------------------------------------------------------------------------
# Polish Content API
# -----------------------------------------------------------------------------


async def polish_content(
    request: PolishContentRequest,
    serviceConfig: ServiceConfig,
) -> Dict[str, Any]:
    """Polish and clean article content.
    
    Args:
        request: The polish request with text and optional config overrides.
        serviceConfig: Default service configuration.
        
    Returns:
        Dictionary with polished_content and changes_made.
    """
    # Resolve effective config
    model = request.model if request.model else serviceConfig.model
    api_key = request.api_key if request.api_key else serviceConfig.api_key
    base_url = request.base_url if request.base_url else serviceConfig.base_url
    
    # Chunk the text
    chunks = chunk_text_by_words(request.text, max_words=1024)
    total_words = count_words(request.text)
    formatted_chunks = format_chunks_for_user_messages(chunks)
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Build messages
    system_prompt = build_polish_content_prompt(
        total_chunks=len(chunks),
        total_words=total_words,
    )
    
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add each chunk as a user message
    for chunk_content in formatted_chunks:
        messages.append({"role": "user", "content": chunk_content})
    
    # Add final instruction
    messages.append({
        "role": "user",
        "content": "Please polish this content and respond with ONLY the JSON object, no other text."
    })
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        
        content = response.choices[0].message.content or "{}"
        result = extract_json_from_response(content)
        
        # Add metadata
        result["model"] = model
        result["total_chunks"] = len(chunks)
        result["total_words"] = total_words
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "model": model,
            "total_chunks": len(chunks),
            "total_words": total_words,
        }


# -----------------------------------------------------------------------------
# Finalize Content API
# -----------------------------------------------------------------------------


async def finalize_content(
    request: FinalizeContentRequest,
    serviceConfig: ServiceConfig,
) -> Dict[str, Any]:
    """Finalize content by extracting metadata and classification.
    
    Args:
        request: The finalize request with text and optional config overrides.
        serviceConfig: Default service configuration.
        
    Returns:
        Dictionary with language, title, keywords, category, and other metadata.
    """
    # Resolve effective config
    model = request.model if request.model else serviceConfig.model
    api_key = request.api_key if request.api_key else serviceConfig.api_key
    base_url = request.base_url if request.base_url else serviceConfig.base_url
    max_keywords = request.max_keywords if request.max_keywords else serviceConfig.max_keywords
    
    # Chunk the text
    chunks = chunk_text_by_words(request.text, max_words=1024)
    total_words = count_words(request.text)
    formatted_chunks = format_chunks_for_user_messages(chunks)
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Build messages
    system_prompt = build_finalize_content_prompt(
        total_chunks=len(chunks),
        total_words=total_words,
        categories=request.categories,
        max_keywords=max_keywords,
    )
    
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add each chunk as a user message
    for chunk_content in formatted_chunks:
        messages.append({"role": "user", "content": chunk_content})
    
    # Add final instruction
    messages.append({
        "role": "user",
        "content": "Please analyze this content and respond with ONLY the JSON object, no other text."
    })
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        
        content = response.choices[0].message.content or "{}"
        result = extract_json_from_response(content)
        
        # Add metadata
        result["model"] = model
        result["total_chunks"] = len(chunks)
        result["total_words"] = total_words
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "model": model,
            "total_chunks": len(chunks),
            "total_words": total_words,
        }


# -----------------------------------------------------------------------------
# Glossary Lookup API
# -----------------------------------------------------------------------------


async def glossary_lookup(
    request: GlossaryLookupRequest,
    serviceConfig: ServiceConfig,
) -> Dict[str, Any]:
    """Look up glossary terms in the text.
    
    Args:
        request: The lookup request with text, glossary, and optional config overrides.
        serviceConfig: Default service configuration.
        
    Returns:
        Dictionary with matches found and occurrence counts.
    """
    # Resolve effective config
    model = request.model if request.model else serviceConfig.model
    api_key = request.api_key if request.api_key else serviceConfig.api_key
    base_url = request.base_url if request.base_url else serviceConfig.base_url
    
    # Chunk the text
    chunks = chunk_text_by_words(request.text, max_words=1024)
    total_words = count_words(request.text)
    formatted_chunks = format_chunks_for_user_messages(chunks)
    
    # Extract glossary term names
    glossary_terms = [entry.term for entry in request.glossary]
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # Build messages
    system_prompt = build_glossary_lookup_prompt(
        total_chunks=len(chunks),
        total_words=total_words,
        glossary_terms=glossary_terms,
    )
    
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Add each chunk as a user message
    for chunk_content in formatted_chunks:
        messages.append({"role": "user", "content": chunk_content})
    
    # Add final instruction
    messages.append({
        "role": "user",
        "content": "Please search for glossary terms and respond with ONLY the JSON object, no other text."
    })
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        
        content = response.choices[0].message.content or "{}"
        result = extract_json_from_response(content)
        
        # Enrich matches with definitions from the original glossary
        if "matches" in result and isinstance(result["matches"], list):
            glossary_dict = {entry.term.lower(): entry for entry in request.glossary}
            for match in result["matches"]:
                term_lower = match.get("term", "").lower()
                if term_lower in glossary_dict:
                    match["definition"] = glossary_dict[term_lower].definition
        
        # Add metadata
        result["model"] = model
        result["total_chunks"] = len(chunks)
        result["total_words"] = total_words
        result["glossary_terms_searched"] = len(glossary_terms)
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "model": model,
            "total_chunks": len(chunks),
            "total_words": total_words,
            "glossary_terms_searched": len(glossary_terms),
        }
