"""Punctuation, Dari, Comma, and Line Break standardization for Bangla text."""

from __future__ import annotations

import re


def format_bangla_punctuation(text: str) -> str:
    """Format and standardize Bangla punctuation (দাঁড়ি, কমা), spacing, and line breaks.

    Rules applied:
    1. Convert English full stops (.) after Bengali letters/words to Bengali Dari (।).
    2. Remove accidental spaces before punctuation (যেমন: 'যাব ।' -> 'যাব।', 'তিনি ,' -> 'তিনি,').
    3. Ensure single space after punctuation when followed by words on the same line (যেমন: 'যাব।আমরা' -> 'যাব। আমরা').
    4. Remove multiple consecutive punctuation marks (যেমন: '।।' -> '।', ',,' -> ',').
    5. Clean up redundant spaces and normalize multiple consecutive blank lines.
    """
    if not text:
        return ""

    formatted = text

    # 1. Convert English dot (.) immediately following Bengali characters to Dari (।)
    # Note: Avoid converting numbers/decimals (e.g., 3.14) or URLs
    formatted = re.sub(r'([\u0980-\u09FF])\s*\.\s*(?=[\s\u0980-\u09FF]|$)', r'\1। ', formatted)

    # 2. Eliminate multiple consecutive Daris (।। -> ।) and commas (,, -> ,)
    formatted = re.sub(r'।{2,}', '।', formatted)
    formatted = re.sub(r',{2,}', ',', formatted)

    # 3. Remove space BEFORE punctuation mark: '।' or ',' or '?' or '!'
    formatted = re.sub(r'\s+([।,?!;:])', r'\1', formatted)

    # 4. Ensure single space AFTER punctuation if followed by a word on the same line
    formatted = re.sub(r'([।,?!;:])([^\s।,?!;:\n\r\)])', r'\1 \2', formatted)

    # 5. Clean up multiple spaces on the same line into a single space
    formatted = re.sub(r'[ \t]+', ' ', formatted)

    # 6. Normalize excessive blank lines (more than 2 consecutive newlines -> 2 newlines)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)

    # 7. Strip leading/trailing whitespace per line
    lines = [line.strip() for line in formatted.splitlines()]
    return "\n".join(lines).strip()
