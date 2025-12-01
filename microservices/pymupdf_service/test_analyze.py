"""Command-line test for PyMuPDF PDF analysis.

Usage:
    python test_analyze.py --file path/to/document.pdf
    python test_analyze.py --file path/to/document.pdf --mode convert
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test PyMuPDF PDF analysis from the command line."
    )
    parser.add_argument(
        "--file", "-f", required=True, help="Path to PDF file to analyze."
    )
    parser.add_argument(
        "--mode",
        choices=["analyze", "convert"],
        default="analyze",
        help="Analysis mode: 'analyze' for full analysis, 'convert' for markdown only.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Optional output file path. If not specified, prints to stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.file)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if not pdf_path.suffix.lower() == ".pdf":
        print(f"Error: File must be a PDF: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Import from main module
    from main import _analyze_pdf, _convert_to_markdown

    try:
        if args.mode == "convert":
            markdown = _convert_to_markdown(str(pdf_path))
            result = {"filename": pdf_path.name, "markdown": markdown}
        else:
            result = _analyze_pdf(str(pdf_path))
            result["filename"] = pdf_path.name
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.json:
        output_text = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        lines = [f"=== {result['filename']} ==="]
        if args.mode == "analyze":
            meta = result.get("metadata", {})
            lines.append(f"Pages: {meta.get('page_count', '?')}")
            if meta.get("title"):
                lines.append(f"Title: {meta['title']}")
            if meta.get("author"):
                lines.append(f"Author: {meta['author']}")

            entities = result.get("entities", [])
            headings = [e for e in entities if e.get("type") == "heading"]
            keywords = [e for e in entities if e.get("type") == "keyword"]

            if headings:
                lines.append(f"\nHeadings ({len(headings)}):")
                for h in headings[:10]:
                    lines.append(f"  - {h['value']}")

            if keywords:
                lines.append(f"\nKeywords ({len(keywords)}):")
                for k in keywords:
                    lines.append(f"  - {k['value']} (score: {k.get('score', '?')})")

            lines.append(f"\n--- Markdown Preview (first 2000 chars) ---")
            md = result.get("markdown", "")
            lines.append(md[:2000])
            if len(md) > 2000:
                lines.append(f"\n... ({len(md) - 2000} more characters)")
        else:
            md = result.get("markdown", "")
            lines.append(md)

        output_text = "\n".join(lines)

    # Output
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Output written to: {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
