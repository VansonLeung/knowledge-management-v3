"""Analysis engine with SSE streaming support.

Handles the main analysis loop, tool execution, and SSE event generation.
"""

from __future__ import annotations

import json
import traceback
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from config import ServiceConfig
from models import CategoryItem, GlossaryEntry, StudyTextRequest
from prompts import (
    build_initial_user_message,
    build_system_prompt,
    build_tool_error_message,
)
from state import AnalysisState
from tools import get_tool_definitions


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
    
    elif tool_name == "extract_lines_as_main_article":
        return state.extract_lines_as_main_article(
            start=arguments["start_line"],
            end=arguments["end_line"],
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
            related_links=arguments.get("related_links", []),
        )
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# -----------------------------------------------------------------------------
# Analysis Engine
# -----------------------------------------------------------------------------


async def analyze_document_stream(
    request: StudyTextRequest,
    serviceConfig: ServiceConfig,
) -> AsyncGenerator[str, None]:
    """Analyze a document with SSE streaming.
    
    Performs iterative LLM analysis with tool calling, streaming
    progress updates via Server-Sent Events.
    
    Args:
        request: The analysis request.
        serviceConfig: Application serviceConfig.
        
    Yields:
        SSE formatted event strings.
    """
    # Create state first so we can get total_lines
    state = AnalysisState(
        text=request.text,
        glossary=request.glossary,
        categories=request.categories,
        max_keywords=serviceConfig.max_keywords,
    )
    
    # Send start event
    yield sse_event("start", {
        "message": "Starting document analysis",
        "total_lines": state.total_lines,
        "total_characters": state.total_characters,
        "model": serviceConfig.model,
        "max_iterations": serviceConfig.max_iterations,
    })
    
    # Initialize OpenAI client
    client = AsyncOpenAI(
        api_key=serviceConfig.api_key,
        base_url=serviceConfig.base_url,
    )
    
    # Build system prompt
    system_prompt = build_system_prompt(
        total_lines=state.total_lines,
        total_characters=state.total_characters,
        has_glossary=len(state.glossary_entries) > 0,
        categories=state.categories,
        max_keywords=state.max_keywords,
    )
    
    # Initialize messages
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_initial_user_message()},
    ]
    
    # Get tool definitions
    tools = get_tool_definitions()
    
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
                model=serviceConfig.model,
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
