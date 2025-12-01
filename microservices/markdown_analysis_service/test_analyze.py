#!/usr/bin/env python3
"""CLI test script for Markdown Analysis Service.

Usage:
    python test_analyze.py <file_or_text> [options]

Examples:
    python test_analyze.py document.md
    python test_analyze.py "Some text to analyze"
    python test_analyze.py document.txt --glossary glossary.json --categories categories.json
    python test_analyze.py doc.md --model gpt-4o --max-hashtags 5
"""

import argparse
import json
import sys
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(
        description="Test Markdown Analysis Service"
    )
    parser.add_argument(
        "input",
        help="Text to analyze, or path to a file containing text"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:16009",
        help="Service URL (default: http://localhost:16009)"
    )
    parser.add_argument(
        "--model",
        help="LLM model to use (default: server default)"
    )
    parser.add_argument(
        "--api-key",
        help="API key (default: server default)"
    )
    parser.add_argument(
        "--base-url",
        help="API base URL (default: server default)"
    )
    parser.add_argument(
        "--max-hashtags",
        type=int,
        help="Maximum hashtags to generate (default: 10)"
    )
    parser.add_argument(
        "--metadata",
        help="Path to JSON file with metadata, or inline JSON"
    )
    parser.add_argument(
        "--glossary",
        help="Path to JSON file with glossary, or inline JSON"
    )
    parser.add_argument(
        "--categories",
        help="Path to JSON file with categories, or inline JSON"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary", "content"],
        default="summary",
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    # Get text input
    input_path = Path(args.input)
    if input_path.exists():
        text = input_path.read_text(encoding="utf-8")
        print(f"Read {len(text):,} characters from {input_path}", file=sys.stderr)
    else:
        text = args.input

    # Build request
    request = {"text": text}

    if args.model:
        request["model"] = args.model
    if args.api_key:
        request["api_key"] = args.api_key
    if args.base_url:
        request["base_url"] = args.base_url
    if args.max_hashtags:
        request["max_hashtags"] = args.max_hashtags

    # Load optional JSON inputs
    for field, arg_value in [
        ("metadata", args.metadata),
        ("glossary", args.glossary),
        ("categories", args.categories),
    ]:
        if arg_value:
            try:
                # Try as file path first
                path = Path(arg_value)
                if path.exists():
                    request[field] = json.loads(path.read_text(encoding="utf-8"))
                else:
                    # Try as inline JSON
                    request[field] = json.loads(arg_value)
            except json.JSONDecodeError as e:
                print(f"Error parsing {field} JSON: {e}", file=sys.stderr)
                sys.exit(1)

    # Send request
    url = f"{args.url.rstrip('/')}/study_text"
    print(f"Sending request to {url}...", file=sys.stderr)

    try:
        response = requests.post(
            url,
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to {args.url}", file=sys.stderr)
        print("Make sure the service is running.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request timed out (>5 minutes)", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}", file=sys.stderr)
        try:
            error = response.json()
            print(f"Detail: {error.get('detail', 'Unknown error')}", file=sys.stderr)
        except Exception:
            print(response.text, file=sys.stderr)
        sys.exit(1)

    data = response.json()

    # Format output
    if args.format == "json":
        output = json.dumps(data, indent=2, ensure_ascii=False)
    elif args.format == "content":
        output = data.get("content", "")
    else:  # summary
        lines = [
            "=" * 60,
            "ANALYSIS RESULTS",
            "=" * 60,
            "",
            f"Language: {data.get('language', 'unknown')}",
            f"Title: {data.get('title', 'Untitled')}",
            "",
            f"Category: {' → '.join(data.get('category', []))}",
            "",
            f"Hashtags: {', '.join('#' + t for t in data.get('hashtags', []))}",
            "",
            f"Iterations used: {data.get('iterations_used', 0)}",
            "",
        ]

        if data.get("glossary_matches"):
            lines.append("Glossary Matches:")
            for match in data["glossary_matches"]:
                lines.append(f"  - {match['term']}: {match['definition']}")
            lines.append("")

        if data.get("extracted_sections"):
            lines.append(f"Extracted Sections: {len(data['extracted_sections'])}")
            for sec in data["extracted_sections"]:
                lines.append(f"  - {sec['name']} (lines {sec['start_line']}-{sec['end_line']})")
            lines.append("")

        if data.get("removed_sections"):
            lines.append(f"Removed Sections: {len(data['removed_sections'])}")
            for sec in data["removed_sections"]:
                lines.append(f"  - Lines {sec['start_line']}-{sec['end_line']} ({sec['reason']})")
            lines.append("")

        lines.extend([
            "=" * 60,
            "CLEANED CONTENT (first 1000 chars)",
            "=" * 60,
            "",
            data.get("content", "")[:1000],
            "..." if len(data.get("content", "")) > 1000 else "",
        ])

        output = "\n".join(lines)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
