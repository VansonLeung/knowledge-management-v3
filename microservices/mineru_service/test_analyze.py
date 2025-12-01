"""Command-line test for MinerU document analysis.

Usage:
    python test_analyze.py --file path/to/document.pdf
    python test_analyze.py --file path/to/image.png --mode convert
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test MinerU document analysis from the command line."
    )
    parser.add_argument(
        "--file", "-f", required=True, help="Path to PDF or image file to analyze."
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

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Import from main module
    from main import _run_mineru

    print(f"Processing: {file_path}", file=sys.stderr)
    print("(First run may download model weights ~10-20GB)", file=sys.stderr)

    try:
        result = _run_mineru(str(file_path))
        result["filename"] = file_path.name
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.json:
        output_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    else:
        lines = [f"=== {result['filename']} ==="]

        pages = result.get("pages", [])
        lines.append(f"Pages: {len(pages)}")

        metadata = result.get("metadata")
        if metadata:
            lines.append(f"Metadata: {metadata}")

        if args.mode == "analyze" and pages:
            lines.append(f"\n--- Page Blocks Summary ---")
            for page in pages[:5]:
                blocks = page.get("blocks", [])
                lines.append(f"Page {page['page']}: {len(blocks)} blocks")
                for b in blocks[:3]:
                    btype = b.get("type", "unknown")
                    text = b.get("text", "")[:100]
                    lines.append(f"  [{btype}] {text}...")
            if len(pages) > 5:
                lines.append(f"  ... and {len(pages) - 5} more pages")

        lines.append(f"\n--- Markdown Preview (first 2000 chars) ---")
        md = result.get("markdown", "")
        lines.append(md[:2000])
        if len(md) > 2000:
            lines.append(f"\n... ({len(md) - 2000} more characters)")

        output_text = "\n".join(lines)

    # Output
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
