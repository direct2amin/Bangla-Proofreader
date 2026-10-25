"""Bijoy (SutonnyMJ / ANSI) to Unicode Bengali converter with Arabic script & URL protection."""

from __future__ import annotations

import re
from typing import List, Tuple

# 1. URL and Email protection regex
URL_EMAIL_PATTERN = re.compile(
    r'(?:https?://|www\.)[^\s<>"]+|(?:[\w\.-]+@[\w\.-]+\.\w+)'
)

# 2. Arabic blocks protection regex (preserves all Arabic characters, harakat, diacritics, and associated quotes)
_ARABIC_CHAR = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
_ARABIC_SEP = r'[\s\u200c\u200d\u060C\u061B\u061F\u06D4\(\)\[\]:–-]'
ARABIC_BLOCK_PATTERN = re.compile(
    rf'[«\(\[]?\s*{_ARABIC_CHAR}+(?:{_ARABIC_SEP}*[«»]?{_ARABIC_CHAR}+)*[»\)\]]?'
)

# Pre-conversion normalization map
PRE_CONVERSION_MAP: List[Tuple[str, str]] = [
    ("  ", " "),
    ("yy", "y"),
    ("vv", "v"),
    ("\u00AD\u00AD", "\u00AD"),
    ("y&", "y"),
    ("\u201E&", "\u201E"),
    ("\u2021u", "u\u2021"),
    ("wu", "uw"),
    (" ,", ","),
    (" |", "|"),
    ("\\\\ ", ""),
    (" \\\\", ""),
    ("\\\\", ""),
    ("\n ", "\n"),
    (" \n", "\n"),
    ("\n\n\n\n\n", "\n\n"),
    ("\n\n\n\n", "\n\n"),
    ("\n\n\n", "\n\n"),
]

# Comprehensive Bijoy/SutonnyMJ to Unicode mapping table
CONVERSION_MAP: List[Tuple[str, str]] = [
    # Multi-character sequences first
    ("i\u00E6", "রু"),
    ("i\u201C", "রু"),
    ("i\u0192", "রূ"),
    ("M\u00F8", "গ্ল"),
    ("\u201DQ\u00A6", "চ্ছ্ব"),
    ("c\u00F8", "প্ল"),
    ("e\u00F8", "ব্ল"),
    ("k\u00F8", "শ্ল"),
    ("\u00A4\u00F8", "ম্ল"),
    ("\u00AF\u00F8", "স্ল"),
    ("\u00E5\u201C", "ভ্রু"),
    ("\u00AF\u00CD\u00A1", "স্ত্ব"),
    ("\u0161\u00CD\u00A1", "ন্ত্ব"),
    ("\u00AF\u00CD", "স্ত"),
    ("\u0161\u00CD", "ন্ত"),
    ("\u00CB\u00A1", "ত্ত্ব"),
    ("\\\\", "॥"),

    # Independent Vowels (Av must come before A)
    ("Av", "আ"),
    ("A", "অ"),
    ("B", "ই"),
    ("C", "ঈ"),
    ("D", "উ"),
    ("E", "ঊ"),
    ("F", "ঋ"),
    ("G", "এ"),
    ("H", "ঐ"),
    ("I", "ও"),
    ("J", "ঔ"),

    # Consonants
    ("K", "ক"), ("L", "খ"), ("M", "গ"), ("N", "ঘ"), ("O", "ঙ"),
    ("P", "চ"), ("Q", "ছ"), ("R", "জ"), ("S", "ঝ"), ("T", "ঞ"),
    ("U", "ট"), ("V", "ঠ"), ("W", "ড"), ("X", "ঢ"), ("Y", "ণ"),
    ("Z", "ত"), ("_", "থ"), ("`", "দ"), ("a", "ধ"), ("b", "ন"),
    ("c", "প"), ("d", "ফ"), ("e", "ব"), ("f", "ভ"), ("g", "ম"),
    ("h", "য"), ("i", "র"), ("j", "ল"), ("k", "শ"), ("l", "ষ"),
    ("m", "স"), ("n", "হ"), ("o", "\u09DC"), ("p", "\u09DD"), ("q", "\u09DF"),
    ("r", "ৎ"), ("s", "ং"), ("t", "ঃ"), ("u", "ঁ"),

    # Digits
    ("0", "০"), ("1", "১"), ("2", "২"), ("3", "৩"), ("4", "৪"),
    ("5", "৫"), ("6", "৬"), ("7", "৭"), ("8", "৮"), ("9", "৯"),

    # Vowel Signs (Kars) and Modifiers
    ("\u2022", "ঙ্"),
    ("v", "া"),
    ("w", "ি"),
    ("x", "ী"),
    ("y", "ু"),
    ("z", "ু"),
    ("\u201C", "ু"),
    ("\u2013", "ু"),
    ("~", "ূ"),
    ("\u0192", "ূ"),
    ("\u201A", "ূ"),
    ("\u201E\u201E", "ৃ"),
    ("\u201E", "ৃ"),
    ("\u2026", "ৃ"),
    ("\u2020", "ে"),
    ("\u2021", "ে"),
    ("\u02C6", "ৈ"),
    ("\u2030", "ৈ"),
    ("\u0160", "ৗ"),
    ("|", "।"),
    ("&", "্\u200C"),

    # Conjunct Glyphs
    ("^", "্ব"),
    ("\u2018", "্তু"),
    ("\u2019", "্থ"),
    ("\u2039", "্ক"),
    ("\u0152", "্ক্র"),
    ("\u201D", "চ্"),
    ("\u2014", "্ত"),
    ("\u02DC", "দ্"),
    ("\u2122", "দ্"),
    ("\u0161", "ন্"),
    ("\u203A", "ন্"),
    ("\u0153", "্ন"),
    ("\u0178", "্ব"),
    ("\u00A1", "্ব"),
    ("\u00A2", "্ভ"),
    ("\u00A3", "্ভ্র"),
    ("\u00A4", "ম্"),
    ("\u00A5", "্ম"),
    ("\u00A6", "্ব"),
    ("\u00A7", "্ম"),
    ("\u00A8", "্য"),
    ("\u00A9", "র্"),
    ("\u00AA", "্র"),
    ("\u00AB", "্র"),
    ("\u00AC", "্ল"),
    ("\u00AD", "্ল"),
    ("\u00AE", "ষ্"),
    ("\u00AF", "স্"),
    ("\u00B0", "ক্ক"),
    ("\u00B1", "ক্ট"),
    ("\u00B2", "ক্ষ্ণ"),
    ("\u00B3", "ক্ত"),
    ("\u00B4", "ক্ম"),
    ("\u00B5", "ক্র"),
    ("\u00B6", "ক্ষ"),
    ("\u00B7", "ক্স"),
    ("\u00B8", "গু"),
    ("\u00B9", "জ্ঞ"),
    ("\u00BA", "গ্দ"),
    ("\u00BB", "গ্ধ"),
    ("\u00BC", "ঙ্ক"),
    ("\u00BD", "ঙ্গ"),
    ("\u00BE", "জ্জ"),
    ("\u00BF", "্ত্র"),
    ("\u00C0", "জ্ঝ"),
    ("\u00C1", "জ্ঞ"),
    ("\u00C2", "ঞ্চ"),
    ("\u00C3", "ঞ্ছ"),
    ("\u00C4", "ঞ্জ"),
    ("\u00C5", "ঞ্ঝ"),
    ("\u00C6", "ট্ট"),
    ("\u00C7", "ড্ড"),
    ("\u00C8", "ণ্ট"),
    ("\u00C9", "ণ্ঠ"),
    ("\u00CA", "ণ্ড"),
    ("\u00CB", "ত্ত"),
    ("\u00CC", "ত্থ"),
    ("\u00CD", "ত্ম"),
    ("\u00CE", "ত্র"),
    ("\u00CF", "দ্দ"),
    ("\u00D0", "-"),
    ("\u00D1", "-"),
    ("\u00D2", '"'),
    ("\u00D3", '"'),
    ("\u00D4", "'"),
    ("\u00D5", "'"),
    ("\u00D6", "্র"),
    ("\u00D7", "দ্ধ"),
    ("\u00D8", "দ্ব"),
    ("\u00D9", "দ্ম"),
    ("\u00DA", "ন্ঠ"),
    ("\u00DB", "ন্ড"),
    ("\u00DC", "ন্ধ"),
    ("\u00DD", "ন্স"),
    ("\u00DE", "প্ট"),
    ("\u00DF", "প্ত"),
    ("\u00E0", "প্প"),
    ("\u00E1", "প্স"),
    ("\u00E2", "ব্জ"),
    ("\u00E3", "ব্দ"),
    ("\u00E4", "ব্ধ"),
    ("\u00E5", "ভ্র"),
    ("\u00E6", "ু"),
    ("\u00E7", "ম্ফ"),
    ("\u00E8", "্ন"),
    ("\u00E9", "ল্ক"),
    ("\u00EA", "ল্গ"),
    ("\u00EB", "ল্ট"),
    ("\u00EC", "ল্ড"),
    ("\u00ED", "ল্প"),
    ("\u00EE", "ল্ফ"),
    ("\u00EF", "শু"),
    ("\u00F0", "শ্চ"),
    ("\u00F1", "শ্ছ"),
    ("\u00F2", "ষ্ণ"),
    ("\u00F3", "ষ্ট"),
    ("\u00F4", "ষ্ঠ"),
    ("\u00F5", "ষ্ফ"),
    ("\u00F6", "স্খ"),
    ("\u00F7", "স্ট"),
    ("\u00F8", "স্ন"),
    ("\u00F9", "স্ফ"),
    ("\u00FA", "্প"),
    ("\u00FB", "হু"),
    ("\u00FC", "হৃ"),
    ("\u00FD", "হ্ন"),
    ("\u00FE", "হ্ম"),
    ("\u00FF", "ক্ষ"),
]

# Pro-conversion map
PRO_CONVERSION_MAP: List[Tuple[str, str]] = [
    ("্্", "্"),
]

# Post-conversion cleanup map
POST_CONVERSION_MAP: List[Tuple[str, str]] = [
    ("০ঃ", "০:"), ("১ঃ", "১:"), ("২ঃ", "২:"), ("৩ঃ", "৩:"), ("৪ঃ", "৪:"),
    ("৫ঃ", "৫:"), ("৬ঃ", "৬:"), ("৭ঃ", "৭:"), ("৮ঃ", "৮:"), ("৯ঃ", "৯:"),
    (" ঃ", ":"), ("\nঃ", "\n:"), ("]ঃ", "]:"), ("[ঃ", "[:"),
    ("  ", " "), ("অা", "আ"), ("্\u200C্\u200C", "্\u200C"),
]

HALANT = "\u09CD"


def apply_map(text: str, mapping: List[Tuple[str, str]]) -> str:
    """Sequentially replace literal substrings according to mapping list."""
    for src, tgt in mapping:
        text = text.replace(src, tgt)
    return text


def is_bangla_pre_kar(c: str) -> bool:
    """Return True if character is a pre-kar (i-kar, oi-kar, e-kar)."""
    return c in ("ি", "ৈ", "ে")


def is_bangla_post_kar(c: str) -> bool:
    """Return True if character is a post-kar."""
    return c in ("া", "ো", "ৌ", "ৗ", "ু", "ূ", "ী", "ৃ")


def is_bangla_kar(c: str) -> bool:
    """Return True if character is any Bengali vowel sign."""
    return is_bangla_pre_kar(c) or is_bangla_post_kar(c)


def is_bangla_banjonborno(c: str) -> bool:
    """Return True if character is a Bengali consonant or modifier."""
    if not c:
        return False
    return c in "কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎংঃঁ"


def is_bangla_nukta(c: str) -> bool:
    return c == "ঁ"


def is_bangla_halant(c: str) -> bool:
    return c == HALANT


def is_space(c: str) -> bool:
    return c in (" ", "\t", "\n", "\r")


def char_at(s: str, i: int) -> str:
    if 0 <= i < len(s):
        return s[i]
    return ""


def rearrange(input_str: str) -> str:
    """Reorder legacy Bijoy positional signs (reph, pre-kars, halants, nuktas) into logical Unicode."""
    s = input_str
    i = 0

    # First pass: handle reph (র + halant) when surrounded by halants
    while i < len(s):
        if (i < len(s) - 1 and char_at(s, i) == "র" and
            is_bangla_halant(char_at(s, i + 1)) and
            is_bangla_halant(char_at(s, i - 1))):
            j = 1
            while True:
                if i - j < 0:
                    break
                if is_bangla_banjonborno(char_at(s, i - j)) and is_bangla_halant(char_at(s, i - j - 1)):
                    j += 2
                elif j == 1 and is_bangla_kar(char_at(s, i - j)):
                    j += 1
                else:
                    break
            s = s[:i - j] + char_at(s, i) + char_at(s, i + 1) + s[i - j:i] + s[i + 2:]
            i += 1
            continue
        i += 1

    # Reph reorder for the trailing-© case: e.g. Kg©KZ©vi -> কর্মকর্তার
    i = 0
    while i < len(s) - 1:
        if (char_at(s, i) == "র" and
            is_bangla_halant(char_at(s, i + 1)) and
            i > 0 and
            is_bangla_banjonborno(char_at(s, i - 1)) and
            not is_bangla_halant(char_at(s, i - 2)) and
            not (is_bangla_banjonborno(char_at(s, i + 2)) and is_bangla_halant(char_at(s, i + 3)))):
            j = 1
            while True:
                if i - j - 1 < 0:
                    break
                if is_bangla_banjonborno(char_at(s, i - j - 1)) and is_bangla_halant(char_at(s, i - j)):
                    j += 2
                else:
                    break
            s = s[:i - j] + char_at(s, i) + char_at(s, i + 1) + s[i - j:i] + s[i + 2:]
            i += 2
            continue
        i += 1

    s = apply_map(s, PRO_CONVERSION_MAP)

    # Second pass: reph, pre-kars, and vowel/halant swaps
    i = 0
    while i < len(s):
        if (i < len(s) - 1 and char_at(s, i) == "র" and
            is_bangla_halant(char_at(s, i + 1)) and
            not is_bangla_halant(char_at(s, i - 1)) and
            is_bangla_halant(char_at(s, i + 2))):
            j = 1
            while True:
                if i - j < 0:
                    break
                if is_bangla_banjonborno(char_at(s, i - j)) and is_bangla_halant(char_at(s, i - j - 1)):
                    j += 2
                elif j == 1 and is_bangla_kar(char_at(s, i - j)):
                    j += 1
                else:
                    break
            s = s[:i - j] + char_at(s, i) + char_at(s, i + 1) + s[i - j:i] + s[i + 2:]
            i += 1
            continue

        # Vowel + halant + consonant -> halant + consonant + vowel
        if (i > 0 and char_at(s, i) == HALANT and
            (is_bangla_kar(char_at(s, i - 1)) or is_bangla_nukta(char_at(s, i - 1))) and
            i < len(s) - 1):
            s = s[:i - 1] + char_at(s, i) + char_at(s, i + 1) + char_at(s, i - 1) + s[i + 2:]

        # র + halant + vowel -> vowel + র + halant
        if (i > 0 and i < len(s) - 1 and
            char_at(s, i) == HALANT and
            char_at(s, i - 1) == "\u09B0" and
            char_at(s, i - 2) != HALANT and
            is_bangla_kar(char_at(s, i + 1))):
            s = s[:i - 1] + char_at(s, i + 1) + char_at(s, i - 1) + char_at(s, i) + s[i + 2:]

        # Pre-kar to post-kar Unicode placement (ি, ৈ, ে)
        if (i < len(s) - 1 and is_bangla_pre_kar(char_at(s, i)) and not is_space(char_at(s, i + 1))):
            temp = s[:i]
            j = 1
            while i + j < len(s) and is_bangla_banjonborno(char_at(s, i + j)):
                if i + j + 1 < len(s) and is_bangla_halant(char_at(s, i + j + 1)):
                    j += 2
                else:
                    break
            temp += s[i + 1:i + j + 1]

            l = 0
            # Split O-kar: ে + consonant + া -> ো
            if char_at(s, i) == "ে" and char_at(s, i + j + 1) == "া":
                temp += "ো"
                l = 1
            # Split Ou-kar: ে + consonant + ৗ -> ৌ
            elif char_at(s, i) == "ে" and char_at(s, i + j + 1) == "ৗ":
                temp += "ৌ"
                l = 1
            else:
                temp += char_at(s, i)

            temp += s[i + j + l + 1:]
            s = temp
            i += j

        # Nukta after kar
        if (i < len(s) - 1 and is_bangla_nukta(char_at(s, i)) and is_bangla_post_kar(char_at(s, i + 1))):
            s = s[:i] + char_at(s, i + 1) + char_at(s, i) + s[i + 2:]

        i += 1

    return s


def convert_bijoy_to_unicode(text: str) -> str:
    """Convert Bijoy/SutonnyMJ text to Unicode with Arabic script and URL/email protection."""
    if not text:
        return text

    # Step 1: Protect URLs and Emails using Private Use Area tokens
    urls: list[str] = []
    def mask_url(m: re.Match) -> str:
        idx = len(urls)
        urls.append(m.group(0))
        return chr(0xE100 + idx)

    text = URL_EMAIL_PATTERN.sub(mask_url, text)

    # Step 2: Protect Arabic text blocks and Harakat using Private Use Area tokens
    arabics: list[str] = []
    def mask_arabic(m: re.Match) -> str:
        idx = len(arabics)
        arabics.append(m.group(0))
        return chr(0xE000 + idx)

    text = ARABIC_BLOCK_PATTERN.sub(mask_arabic, text)

    # Step 3: Run Bijoy to Unicode mapping pipeline
    out = apply_map(text, PRE_CONVERSION_MAP)
    out = apply_map(out, CONVERSION_MAP)
    out = rearrange(out)
    out = apply_map(out, POST_CONVERSION_MAP)

    # Step 4: Restore Arabic text blocks intact
    for idx, b in enumerate(arabics):
        out = out.replace(chr(0xE000 + idx), b)

    # Step 5: Restore URLs and Emails intact
    for idx, u in enumerate(urls):
        out = out.replace(chr(0xE100 + idx), u)

    return out


def is_bijoy_text(text: str) -> bool:
    """Detect Bijoy/SutonnyMJ signatures in the text.

    Returns False if text is already standard Unicode Bengali or plain English.
    """
    if not text or not text.strip():
        return False

    # If the text already contains standard Unicode Bengali, it does not need conversion
    if re.search(r'[\u0980-\u09FF]', text):
        return False

    # Remove URLs, emails, and Arabic blocks before checking signatures
    clean = URL_EMAIL_PATTERN.sub('', text)
    clean = ARABIC_BLOCK_PATTERN.sub('', clean).strip()
    if not clean:
        return False

    # 1. Distinctive Bijoy/Sutonny legacy ANSI characters
    BIJOY_CHARS = (
        '‡', '†', '‰', 'œ', '®', '¯', 'µ', '¶', '§', '¨', '©', 'ª', '«', '¬',
        '°', '±', '²', '³', '´', '·', '¸', '¹', 'º', '»', '¼', '½', '¾', '¿',
        'À', 'Á', 'Â', 'Ã', 'Ä', 'Å', 'Æ', 'Ç', 'È', 'É', 'Ê', 'Ë', 'Ì', 'Í',
        'Î', 'Ï', 'Ð', 'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', '×', 'Ø', 'Ù', 'Ú', 'Û',
        'Ü', 'Ý', 'Þ', 'ß', 'à', 'á', 'â', 'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é',
        'ê', 'ë', 'ì', 'í', 'î', 'ï', 'ð', 'ñ', 'ò', 'ó', 'ô', 'õ', 'ö', '÷',
        'ø', 'ù', 'ú', 'û', 'ü', 'ý', 'þ', 'ÿ',
        'Œ', 'Š', 'š', 'Ÿ', 'ƒ', 'ˆ', '˜', '™', '›', 'ž', '‘', '’', '“', '”',
        '•', '–', '—', '‹'
    )
    for ch in BIJOY_CHARS:
        if ch in clean:
            return True

    # 2. Distinctive Bijoy ASCII bigram/trigram patterns
    bijoy_patterns = [
        r'\bAv',            # Word starting with Av (আ)
        r'Avgvi',          # আমার
        r'Avwg',           # আমি
        r'evsjv',          # বাংলা
        r'`[a-zA-Z]',      # backtick as 'দ' before letters
        r'[a-zA-Z]`',      # backtick as 'দ' after letters
        r'\bw[K-Za-km-n]', # w (i-kar) before consonant at word start: wK, wZ, w`, wm, etc.
        r'[K-Za-km-n]v[K-Za-km-n]', # Consonant + v (aa-kar) + Consonant
        r'[K-Za-km-n]y',   # Consonant + y (u-kar)
        r'[K-Za-km-n]x',   # Consonant + x (ii-kar)
        r'[K-Za-km-n]s',   # Consonant + s (anusvara)
    ]
    if re.search(r'\b(Avgvi|Avwg|evsjv|‡mvbvi|w`em)\b', clean):
        return True
    if '`' in clean or 'Av' in clean:
        return True

    matches = sum(1 for p in bijoy_patterns if re.search(p, clean))
    return matches >= 2
