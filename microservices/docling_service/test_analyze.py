#!/usr/bin/env python3
"""CLI test script for Docling Service.

Usage:
    python test_analyze.py <file_path> [--endpoint=analyze|convert/to-markdown] [--url=http://localhost:16008]

Examples:
    python test_analyze.py document.pdf
    python test_analyze.py presentation.pptx --endpoint=analyze
    python test_analyze.py spreadsheet.xlsx --endpoint=convert/to-markdown
    python test_analyze.py audio.mp3 --url=http://localhost:16008
"""

import argparse
import json
import sys
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(
        description="Test Docling Service document conversion"
    )
    parser.add_argument("file", help="Path to file to convert")
    parser.add_argument(
        "--endpoint",
        choices=["analyze", "convert/to-markdown"],
        default="analyze",
        help="API endpoint to use (default: analyze)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:16008",
        help="Docling service URL (default: http://localhost:16008)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Build request URL
    url = f"{args.url.rstrip('/')}/{args.endpoint}"
    print(f"Sending {file_path.name} to {url}...", file=sys.stderr)

    # Send request
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = requests.post(url, files=files, timeout=300)
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to {args.url}", file=sys.stderr)
        print("Make sure the Docling service is running.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request timed out (>5 minutes)", file=sys.stderr)
        sys.exit(1)

    # Handle response
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
    elif args.format == "markdown":
        output = data.get("markdown", "")
    else:  # text
        lines = []
        lines.append(f"Filename: {data.get('filename', 'unknown')}")
        lines.append(f"Format: {data.get('format', 'unknown')}")
        
        if "metadata" in data and data["metadata"]:
            lines.append(f"Status: {data['metadata'].get('status', 'unknown')}")
        
        if "pages" in data:
            lines.append(f"Pages: {len(data['pages'])}")
        
        if "tables" in data:
            lines.append(f"Tables: {len(data['tables'])}")
        
        lines.append("")
        lines.append("=== MARKDOWN ===")
        lines.append(data.get("markdown", ""))
        
        if data.get("tables"):
            lines.append("")
            lines.append("=== TABLES ===")
            for i, table in enumerate(data["tables"], 1):
                lines.append(f"\n--- Table {i} ({table['rows']}×{table['columns']}) ---")
                lines.append(table.get("markdown", ""))
        
        output = "\n".join(lines)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    # Summary
    print("", file=sys.stderr)
    print("=== Summary ===", file=sys.stderr)
    print(f"Format: {data.get('format', 'unknown')}", file=sys.stderr)
    if data.get("markdown"):
        print(f"Markdown length: {len(data['markdown']):,} characters", file=sys.stderr)
    if data.get("pages"):
        print(f"Pages: {len(data['pages'])}", file=sys.stderr)
    if data.get("tables"):
        print(f"Tables: {len(data['tables'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
