import argparse
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from main import ChunkingRequest, perform_chunking

SAMPLE_ENGLISH = (
    "LangChain chunking works best when sentences stay together. "
    "This sample mixes short and long sentences, including abbreviations like e.g. "
    "to see how separators behave. The goal is to observe chunk sizes and overlaps "
    "without needing a running API."
)
SAMPLE_CHINESE = (
    "這是一段用來測試中文斷句的文字。它包含多個句子，使用常見的標點符號，"
    "例如，逗號、頓號、以及句號。透過這個示例，可以檢查分塊結果是否保持語義連貫，"
    "並且分隔符是否被保留。"
)


def parse_separators(raw_value: Optional[str]) -> Optional[List[str]]:
    if not raw_value:
        return None
    parts: List[str] = []
    for item in raw_value.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        cleaned = cleaned.replace("\\n", "\n").replace("\\t", "\t")
        parts.append(cleaned)
    return parts or None


def load_cases(args: argparse.Namespace) -> Sequence[Tuple[str, str, Optional[str]]]:
    if args.text:
        return [("inline", args.text, args.language)]
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        return [(args.file, text, args.language)]
    return [
        ("english_sample", SAMPLE_ENGLISH, args.language or "english"),
        ("chinese_sample", SAMPLE_CHINESE, args.language or "chinese"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quickly test the chunking logic without running the HTTP server."
    )
    parser.add_argument("--text", help="Inline text to chunk. Overrides samples.")
    parser.add_argument("--file", help="Path to a UTF-8 text file to chunk.")
    parser.add_argument("--language", help="Language hint such as english or chinese.")
    parser.add_argument(
        "--chunk-size", type=int, default=500, help="Target chunk size (default: 500)."
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="Chunk overlap characters (default: 50).",
    )
    parser.add_argument(
        "--separators",
        help="Comma separated separators (use \\n for newline, \\t for tab).",
    )
    parser.add_argument(
        "--drop-separator",
        action="store_true",
        help="Remove separators from chunks instead of keeping them.",
    )
    args = parser.parse_args()

    separators = parse_separators(args.separators)
    keep_separator = not args.drop_separator

    for label, text, language_hint in load_cases(args):
        request = ChunkingRequest(
            text=text,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            language_hint=language_hint,
            separators=separators,
            keep_separator=keep_separator,
            metadata={"source": label},
        )
        response = perform_chunking(request)
        print(f"\n=== {label} ({len(response.chunks)} chunks) ===")
        for chunk in response.chunks:
            idx = chunk.metadata.get("chunk_index", "?")
            print(f"[{idx}] len={len(chunk.text)} meta={chunk.metadata}")
            print(chunk.text)
            print("-" * 40)


if __name__ == "__main__":
    main()
