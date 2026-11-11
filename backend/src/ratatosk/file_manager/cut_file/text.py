import re
from pathlib import Path

# Regex more technical to the more simple
BOUNDARIES = [
    # 1. Code / Markdown
    re.compile(
        r"\n(?=\n*(?:def |class |async def |fn |pub |struct |impl |func |export |const |let |var |type |interface |# |## ))"
    ),
    # 2. Code
    re.compile(r"\n\n(?=[a-zA-Z0-9_@/#])"),
    # 3. texte
    re.compile(r"\n\s*\n"),
    # 4. end of line
    re.compile(r"\n"),
    # 5. dot at the end of a sentence
    re.compile(r"[.!?]\s+"),
    # 6. space
    re.compile(r"\s+"),
]


def decode_smart(raw_bytes: bytes, truncated: bool = False) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError as exc:
            # If a valid UTF-8 stream was simply sliced mid-codepoint at the end, keep UTF-8
            if (
                enc == "utf-8-sig"
                and truncated
                and exc.reason == "unexpected end of data"
            ):
                return raw_bytes[: exc.start].decode(enc)
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def read_smart_chunk(
    file_path: Path,
    target_kb: int = 64,
    margin_kb: int = 8,
    encoding: str = "auto",
) -> tuple[str, bool]:
    target_bytes = target_kb * 1024
    margin_bytes = margin_kb * 1024
    max_read = target_bytes + margin_bytes

    with file_path.open("rb") as f:
        raw_probe = f.read(max_read + 1)

    reached_eof = len(raw_probe) <= max_read
    raw_data = raw_probe[:max_read]

    def _decode(data: bytes, is_cut: bool) -> str:
        if encoding == "auto":
            return decode_smart(data, truncated=is_cut)
        return data.decode(encoding, errors="replace")

    if len(raw_data) <= target_bytes:
        return _decode(raw_data, is_cut=False), True

    text = _decode(raw_data, is_cut=not reached_eof)

    ratio = len(text) / len(raw_data)
    target_idx = int(target_bytes * ratio)
    margin_idx = int(margin_bytes * ratio)

    window_start = max(0, target_idx - margin_idx)
    search_window = text[window_start:]
    ideal_offset = target_idx - window_start

    for pattern in BOUNDARIES:
        matches = list(pattern.finditer(search_window))
        if matches:
            best_match = min(matches, key=lambda m: abs(m.end() - ideal_offset))
            cut_index = window_start + best_match.end()
            chunk = text[:cut_index].rstrip()
            is_complete = reached_eof and len(chunk) == len(text.rstrip())
            return chunk, is_complete

    return text[:target_idx], False
