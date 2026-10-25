"""Word-level diff calculation, fine-grained alignment, and HTML highlighting."""

from __future__ import annotations

import difflib
import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Set

from app.core.theme import get_diff_spans

# Matches words (including Bengali unicode characters \u0980-\u09FF),
# punctuation, and whitespace sequences.
TOKEN_PATTERN = re.compile(r'[\w\u0980-\u09FF]+|[^\w\s\u0980-\u09FF]+|\s+')
PUNCT_OR_SPACE_PATTERN = re.compile(r'^[\s\.,।\?!:;\-\(\)"\'“”‘’\\/«»—]+$')


def tokenize(text: str) -> list[str]:
    """Tokenize text into words, punctuation, and whitespace preserving original order."""
    if not text:
        return []
    return TOKEN_PATTERN.findall(text)


def is_word(token: str) -> bool:
    """Return True if token represents a word (contains letters/digits)."""
    if not token or PUNCT_OR_SPACE_PATTERN.match(token):
        return False
    return bool(re.search(r'[\w\u0980-\u09FF]', token))


@dataclass
class ChangeRecord:
    change_id: int
    change_type: str  # 'replace', 'insert', 'delete'
    original: str
    corrected: str
    accepted: bool = True


@dataclass
class DiffResult:
    original_html: str
    corrected_html: str
    inline_html: str
    changes: list[ChangeRecord] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    corrected_text: str = ""
    # Raw token structures for dynamic recalculation
    orig_tokens: list[str] = field(default_factory=list)
    corr_tokens: list[str] = field(default_factory=list)
    opcodes: list[tuple] = field(default_factory=list)


def align_words_dp(orig_words: list[str], corr_words: list[str]) -> list[tuple[str, int, int, int, int]]:
    """
    Fine-grained dynamic programming alignment between word lists.
    Prevents multi-word grouping while properly handling compound words (merge/split).
    Returns list of (op, wi1, wi2, wj1, wj2).
    """
    n, m = len(orig_words), len(corr_words)
    band = max(35, abs(n - m) + 20)
    dp: dict[tuple[int, int], tuple[float, int, int, str]] = {}
    dp[(0, 0)] = (0.0, -1, -1, 'start')

    for i in range(n + 1):
        j_min = max(0, i - band)
        j_max = min(m, i + band)
        for j in range(j_min, j_max + 1):
            if (i, j) not in dp:
                continue
            cur_score = dp[(i, j)][0]

            # 1. Delete orig[i] (1 -> 0)
            if i < n:
                score = cur_score - 0.5
                key = (i + 1, j)
                if key not in dp or score > dp[key][0]:
                    dp[key] = (score, i, j, 'delete')

            # 2. Insert corr[j] (0 -> 1)
            if j < m:
                score = cur_score - 0.5
                key = (i, j + 1)
                if key not in dp or score > dp[key][0]:
                    dp[key] = (score, i, j, 'insert')

            # 3. 1 -> 1 (equal or replace)
            if i < n and j < m:
                w1, w2 = orig_words[i], corr_words[j]
                if w1 == w2:
                    score = cur_score + 2.0
                    op = 'equal'
                else:
                    sim = difflib.SequenceMatcher(None, w1, w2, autojunk=False).ratio()
                    score = cur_score + (sim * 2.2 if sim >= 0.4 else -1.5)
                    op = 'replace'
                key = (i + 1, j + 1)
                if key not in dp or score > dp[key][0]:
                    dp[key] = (score, i, j, op)

            # 4. Compound merge (2->1, 3->1)
            for k in (2, 3):
                if i + k <= n and j < m:
                    merged = "".join(orig_words[i:i + k])
                    target = corr_words[j]
                    sim = difflib.SequenceMatcher(None, merged, target, autojunk=False).ratio()
                    if merged == target or sim >= 0.75:
                        score = cur_score + (1.95 if merged == target else sim * 2.0)
                        key = (i + k, j + 1)
                        if key not in dp or score > dp[key][0]:
                            dp[key] = (score, i, j, f'merge_{k}')

            # 5. Compound split (1->2, 1->3)
            for k in (2, 3):
                if i < n and j + k <= m:
                    merged = "".join(corr_words[j:j + k])
                    target = orig_words[i]
                    sim = difflib.SequenceMatcher(None, target, merged, autojunk=False).ratio()
                    if merged == target or sim >= 0.75:
                        score = cur_score + (1.95 if merged == target else sim * 2.0)
                        key = (i + 1, j + k)
                        if key not in dp or score > dp[key][0]:
                            dp[key] = (score, i, j, f'split_{k}')

    # Backtrack path
    curr_i, curr_j = n, m
    ops: list[tuple[str, int, int, int, int]] = []
    while curr_i > 0 or curr_j > 0:
        if (curr_i, curr_j) not in dp:
            break
        score, pi, pj, op = dp[(curr_i, curr_j)]
        ops.append((op, pi, curr_i, pj, curr_j))
        curr_i, curr_j = pi, pj

    ops.reverse()
    return ops


class DiffHighlighter:
    """Calculates word-level differences and produces rich HTML markup."""

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML and preserve newlines."""
        escaped = html.escape(text)
        return escaped.replace("\n", "<br/>")

    @classmethod
    def compute_diff(cls, original: str, corrected: str, is_dark: bool = False) -> DiffResult:
        """Compute fine-grained word-level diff between original and corrected texts."""
        original = unicodedata.normalize('NFC', original)
        corrected = unicodedata.normalize('NFC', corrected)

        orig_tokens = tokenize(original)
        corr_tokens = tokenize(corrected)

        if not orig_tokens and not corr_tokens:
            return DiffResult(
                original_html="", corrected_html="", inline_html="",
                changes=[], stats={"total_suggestions": 0, "accepted_changes": 0, "rejected_changes": 0,
                                   "original_words": 0, "corrected_words": 0},
                corrected_text="", orig_tokens=[], corr_tokens=[], opcodes=[]
            )

        orig_words_info = [(idx, t) for idx, t in enumerate(orig_tokens) if is_word(t)]
        corr_words_info = [(idx, t) for idx, t in enumerate(corr_tokens) if is_word(t)]

        # If either side has no words (pure punctuation/whitespace), fallback to token matcher
        if not orig_words_info or not corr_words_info:
            matcher = difflib.SequenceMatcher(None, orig_tokens, corr_tokens, autojunk=False)
            token_opcodes = matcher.get_opcodes()
        else:
            orig_words = [w for _, w in orig_words_info]
            corr_words = [w for _, w in corr_words_info]
            word_ops = align_words_dp(orig_words, corr_words)

            token_opcodes = []
            last_o = 0
            last_c = 0
            n = len(orig_words)
            m = len(corr_words)

            for op, wi1, wi2, wj1, wj2 in word_ops:
                o_start = orig_words_info[wi1][0] if wi1 < n else len(orig_tokens)
                o_end = orig_words_info[wi2 - 1][0] + 1 if wi2 > 0 and wi2 <= n else o_start

                c_start = corr_words_info[wj1][0] if wj1 < m else len(corr_tokens)
                c_end = corr_words_info[wj2 - 1][0] + 1 if wj2 > 0 and wj2 <= m else c_start

                # Intervening non-word tokens (spaces, punctuation)
                inter_o = orig_tokens[last_o:o_start]
                inter_c = corr_tokens[last_c:c_start]
                if inter_o or inter_c:
                    str_o = "".join(inter_o)
                    str_c = "".join(inter_c)
                    if str_o == str_c or (str_o.strip() == "" and str_c.strip() == ""):
                        token_opcodes.append(('equal', last_o, o_start, last_c, c_start))
                    else:
                        tag = 'insert' if not inter_o else ('delete' if not inter_c else 'replace')
                        token_opcodes.append((tag, last_o, o_start, last_c, c_start))

                # Word operation
                if op == 'equal':
                    token_opcodes.append(('equal', o_start, o_end, c_start, c_end))
                elif op == 'delete':
                    token_opcodes.append(('delete', o_start, o_end, c_start, c_end))
                elif op == 'insert':
                    token_opcodes.append(('insert', o_start, o_end, c_start, c_end))
                else:  # replace, merge, split
                    token_opcodes.append(('replace', o_start, o_end, c_start, c_end))

                last_o = o_end
                last_c = c_end

            # Trailing non-word tokens
            if last_o < len(orig_tokens) or last_c < len(corr_tokens):
                str_o = "".join(orig_tokens[last_o:])
                str_c = "".join(corr_tokens[last_c:])
                if str_o == str_c or (str_o.strip() == "" and str_c.strip() == ""):
                    token_opcodes.append(('equal', last_o, len(orig_tokens), last_c, len(corr_tokens)))
                else:
                    tag = 'insert' if last_o == len(orig_tokens) else ('delete' if last_c == len(corr_tokens) else 'replace')
                    token_opcodes.append((tag, last_o, len(orig_tokens), last_c, len(corr_tokens)))

        # Sanitize opcodes: if replace chunk has identical normalized text, mark as equal
        clean_opcodes = []
        for tag, i1, i2, j1, j2 in token_opcodes:
            orig_chunk = "".join(orig_tokens[i1:i2])
            corr_chunk = "".join(corr_tokens[j1:j2])

            if tag == "replace":
                norm_orig = unicodedata.normalize('NFC', orig_chunk).strip()
                norm_corr = unicodedata.normalize('NFC', corr_chunk).strip()
                if norm_orig == norm_corr:
                    tag = "equal"

            clean_opcodes.append((tag, i1, i2, j1, j2))

        changes: list[ChangeRecord] = []
        change_counter = 0

        for tag, i1, i2, j1, j2 in clean_opcodes:
            orig_chunk = "".join(orig_tokens[i1:i2])
            corr_chunk = "".join(corr_tokens[j1:j2])

            if tag in ("replace", "insert", "delete"):
                changes.append(ChangeRecord(
                    change_id=change_counter,
                    change_type=tag,
                    original=orig_chunk,
                    corrected=corr_chunk,
                    accepted=True
                ))
                change_counter += 1

        result = cls.render_from_opcodes(
            orig_tokens=orig_tokens,
            corr_tokens=corr_tokens,
            opcodes=clean_opcodes,
            changes=changes,
            accepted_ids={c.change_id for c in changes},
            is_dark=is_dark
        )
        return result

    @classmethod
    def render_from_opcodes(
        cls,
        orig_tokens: list[str],
        corr_tokens: list[str],
        opcodes: list[tuple],
        changes: list[ChangeRecord],
        accepted_ids: Set[int],
        is_dark: bool = False,
    ) -> DiffResult:
        """Re-render HTML and final text based on accepted change IDs and active theme."""
        orig_html_parts: list[str] = []
        corr_html_parts: list[str] = []
        inline_html_parts: list[str] = []
        final_text_parts: list[str] = []

        spans = get_diff_spans(is_dark)
        del_style = spans["del_style"]
        del_inline_style = spans.get("del_inline_style", del_style)
        ins_style = spans["ins_style"]

        change_idx = 0
        accepted_count = 0

        for tag, i1, i2, j1, j2 in opcodes:
            orig_chunk = "".join(orig_tokens[i1:i2])
            corr_chunk = "".join(corr_tokens[j1:j2])

            if tag == "equal":
                esc_orig = cls._escape(orig_chunk)
                esc_corr = cls._escape(corr_chunk)
                orig_html_parts.append(esc_orig)
                corr_html_parts.append(esc_corr)
                inline_html_parts.append(esc_orig)
                final_text_parts.append(corr_chunk if corr_chunk else orig_chunk)

            else:
                is_accepted = change_idx in accepted_ids
                change_idx += 1

                if is_accepted:
                    accepted_count += 1
                    esc_orig = cls._escape(orig_chunk)
                    esc_corr = cls._escape(corr_chunk)

                    if tag == "replace":
                        orig_html_parts.append(
                            f'<span class="diff-del" style="{del_style}">{esc_orig}</span>'
                        )
                        corr_html_parts.append(
                            f'<span class="diff-ins" style="{ins_style}">{esc_corr}</span>'
                        )
                        inline_html_parts.append(
                            f'<span class="diff-del" style="{del_inline_style}">{esc_orig}</span> '
                            f'<span class="diff-ins" style="{ins_style}">{esc_corr}</span>'
                        )
                        final_text_parts.append(corr_chunk)

                    elif tag == "insert":
                        corr_html_parts.append(
                            f'<span class="diff-ins" style="{ins_style}">{esc_corr}</span>'
                        )
                        inline_html_parts.append(
                            f'<span class="diff-ins" style="{ins_style}">{esc_corr}</span>'
                        )
                        final_text_parts.append(corr_chunk)

                    elif tag == "delete":
                        orig_html_parts.append(
                            f'<span class="diff-del" style="{del_style}">{esc_orig}</span>'
                        )
                        inline_html_parts.append(
                            f'<span class="diff-del" style="{del_inline_style}">{esc_orig}</span>'
                        )
                        # delete chunk omitted from final_text

                else:
                    # Change was rejected by user -> keep original text unchanged
                    esc_orig = cls._escape(orig_chunk)
                    orig_html_parts.append(esc_orig)
                    corr_html_parts.append(esc_orig)
                    inline_html_parts.append(esc_orig)
                    final_text_parts.append(orig_chunk)

        stats = {
            "total_suggestions": len(changes),
            "total_changes": len(changes),
            "accepted_changes": accepted_count,
            "rejected_changes": len(changes) - accepted_count,
            "original_words": len([t for t in orig_tokens if is_word(t)]),
            "corrected_words": len([t for t in tokenize("".join(final_text_parts)) if is_word(t)]),
        }

        return DiffResult(
            original_html="".join(orig_html_parts),
            corrected_html="".join(corr_html_parts),
            inline_html="".join(inline_html_parts),
            changes=changes,
            stats=stats,
            corrected_text="".join(final_text_parts),
            orig_tokens=orig_tokens,
            corr_tokens=corr_tokens,
            opcodes=opcodes,
        )
