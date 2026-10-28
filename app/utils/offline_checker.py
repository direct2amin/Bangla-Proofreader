"""Conservative Local Offline Spell Checker for Bangla Proofreader.

Loads `assets/dict/bangla_words.txt` (~140,000+ words) into an in-memory Python `set`
for O(1) membership lookups, performs Bengali inflectional suffix stemming
(['র', 'ের', 'য়', 'ে', 'তে', 'কে', 'রা', 'দের', 'গুলো', 'খানি', 'টা', 'টি']),
includes rich Islamic/Arabic-Persian vocabulary, and uses a strictly conservative
edit-distance-1 orthographic threshold so valid or inflected words are never distorted.
"""

from __future__ import annotations

import logging
import os
import re
import time
import unicodedata
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from app.core.assets import get_asset_path
from app.utils.bd_gazetteer import apply_gazetteer_corrections
from app.utils.bijoy_converter import convert_bijoy_to_unicode, is_bijoy_text
from app.utils.foreign_words import is_arabic_word, is_foreign_word

logger = logging.getLogger(__name__)

# Matches Bengali word tokens vs non-word separators (whitespace, punctuation, Arabic, Latin, digits)
BANGLA_TOKEN_PATTERN = re.compile(r"([\u0980-\u09FF\u200c]+|[^\u0980-\u09FF\u200c]+)")
PURE_BANGLA_WORD_RE = re.compile(r"^[\u0980-\u09FF\u200c]+$")
BANGLA_DIGITS_RE = re.compile(r"^[\u09E6-\u09EF]+$")


def normalize_bangla_word(w: str) -> str:
    """Normalize a Bengali word to NFC while keeping ড়, ঢ়, য় as single precomposed codepoints."""
    s = unicodedata.normalize("NFC", w.strip())
    return (
        s.replace("\u09a1\u09bc", "\u09dc")
        .replace("\u09a2\u09bc", "\u09dd")
        .replace("\u09af\u09bc", "\u09df")
    )


# Standard Bengali inflectional suffixes and clitics in order of length (longest first)
MORPH_SUFFIXES: Tuple[str, ...] = (
    "গুলোর", "গুলিতে", "গুলো", "গুলি", "দেরকে", "দের",
    "খানা", "খানি", "তেই", "তে", "ের", "কে", "রে", "রা",
    "টা", "টি", "য়", "ে", "র",
)

INFLECTION_SUFFIXES: Tuple[str, ...] = (
    "গুলোকে", "গুলোতে", "গুলোর", "গুলোয়", "গুলোই", "গুলো", "গুলি",
    "দেরকে", "দেরই", "দের",
    "টিকে", "টিতে", "টির", "টিই", "টি",
    "টাকে", "টাতে", "টার", "টাই", "টা",
    "খানাকে", "খানাতে", "খানার", "খানা", "খানি",
    "বৃন্দ", "সমূহ", "মণ্ডলী", "গণ",
    "তেই", "তে", "কে", "রে", "রা", "ের", "য়ে",
    "র", "য়", "ে", "ই", "ও",
)

# Comprehensive Islamic, Arabic-Persian, and cultural root & inflected vocabulary
ISLAMIC_AND_CULTURAL_VOCAB: Set[str] = {
    normalize_bangla_word(w)
    for w in [
        "খুতবা", "খুতবায়", "খুতবার", "খুতবাতে", "খুৎবা", "খুৎবায়", "খুৎবার",
        "ইলম", "ইলমের", "ইলমে", "ইলমি", "ইলমী", "ইলিম", "ইলিমের", "ইলিমে",
        "দাওয়াত", "দাওয়াতের", "দাওয়াতে", "দাওয়াতি", "দাওয়াতী",
        "রুজি", "রুজির", "রুজিতে", "রিজিক", "রিজিকের", "রিযিক", "রিযিকের",
        "রুটি", "রুটির", "হাদিস", "হাদিসের", "হাদিসে", "হাদীস", "হাদীসের", "হাদীসে",
        "কুরআন", "কুরআনের", "কুরআনে", "কোরআন", "কোরআনের", "কোরআনে",
        "ইবাদত", "ইবাদতের", "ইবাদতে", "এবাদত", "এবাদতের", "এবাদতে",
        "আমল", "আমলের", "আমলে", "আখলাক", "আখলাকের", "ঈমান", "ঈমানের", "ইমান", "ইমানের",
        "সালাত", "সালাতের", "নামাজ", "নামাজের", "নামায", "নামাযের", "রোজা", "রোজার", "রোযা", "সাওম", "সিয়াম",
        "যাকাত", "যাকাতের", "জাকাত", "হজ", "হজের", "হজ্জ", "হজ্জের", "উমরাহ", "ওমরাহ",
        "সুন্নত", "সুন্নতের", "সুন্নাহ", "সুন্নাহর", "ফরজ", "ফরজের", "ফরয", "ওয়াজিব", "মুস্তাহাব",
        "মাকরুহ", "হালাল", "হারাম", "জায়েজ", "জায়েয", "নাজায়েজ", "নাজায়েয",
        "তাকওয়া", "তাকওয়ার", "তাওয়াক্কুল", "সবর", "শুকর", "শোকর", "তওবা", "তাওবা",
        "ইস্তিগফার", "জিকির", "যিকির", "দোয়া", "দোয়ার", "দুআ", "দুআর", "মুনাজাত", "মোনাজাত",
        "আলেম", "আলেমদের", "উলামা", "ওলামা", "উলামায়ে", "ওলামায়ে", "মুফতি", "মুফতী",
        "মুহাদ্দিস", "মুফাসসির", "হাফেজ", "হাফেয", "ক্বারী", "কারী", "ইমাম", "ইমামের",
        "মুয়াজ্জিন", "মুআজ্জিন", "খতিব", "খতীব", "মসজিদ", "মসজিদের", "মসজিদে",
        "মাদ্রাসা", "মাদ্রাসার", "মাদ্রাসায়", "মাদরাসা", "মাদরাসার", "মাদরাসায়", "মক্তব", "খানকাহ",
        "উস্তাদ", "উস্তাদের", "ওস্তাদ", "ওস্তাদের", "শায়েখ", "শায়খ", "পীর", "মুরিদ",
        "তালিবুল", "তালেবে", "সবক", "দরস", "তাদরিস", "তাসনিফ", "তাহকিক", "তাহকীক",
        "ফতোয়া", "ফতোয়ার", "ফাতওয়া", "মাসআলা", "মাসয়ালা", "মাসায়েল", "ফিকহ", "ফিকাহ",
        "আকিদা", "আকীদা", "তাফসির", "তাফসীর", "সিরাত", "সীরাত", "সাহাবি", "সাহাবী",
        "সাহাবা", "সাহাবাদের", "তাবেঈ", "তাবেয়ী", "সালাফ", "উম্মত", "উম্মতের", "উম্মাহ", "উম্মাহর",
        "জান্নাত", "জান্নাতের", "জান্নাতে", "জাহান্নাম", "জাহান্নামের", "আখিরাত", "আখিরাতের",
        "আখেরাত", "আখেরাতের", "কিয়ামত", "কিয়ামতের", "কেয়ামত", "কেয়ামতের", "কবর", "কবরের",
        "হাশর", "হাশরের", "মিজান", "পুলসিরাত", "শাফায়াত", "শাফাআত",
        "রহমত", "রহমতের", "বরকত", "বরকতের", "মাগফিরাত", "মাগফিরাতের",
        "হেদায়েত", "হেদায়াত", "হিদায়াত", "নেয়ামত", "নিয়ামত", "তওফিক", "তাওফিক", "তাওফীক",
        "হক", "হকের", "বাতিল", "ইনসাফ", "আমানত", "খেয়ানত", "গিবত", "গীবত", "ইখলাস", "ইখলাসের",
        "সুন্নতি", "সুন্নতী", "নফল", "তাহাজ্জুদ", "ইশরাক", "চাশত", "আওয়াবিন", "তারাবি", "তারাবীহ",
        "ইতিকাফ", "ইতেকাফ", "সদকা", "সাদাকাহ", "ফিতরা", "কুরবানি", "কোরবানি", "আকিকা", "আকীকা",
        "জুমুআ", "জুমা", "জুমার", "জুমআ", "জুমআর", "ঈদ", "ঈদের", "রমজান", "রমযান", "রমজানের",
        "শাবান", "রজব", "মহররম", "শাওয়াল", "জিলহজ", "জিলকদ",
    ]
}

# High-precision Bangla Academy standard correction rules for instant O(1) mapping
DIRECT_CORRECTIONS: Dict[str, str] = {
    normalize_bangla_word(k): normalize_bangla_word(v)
    for k, v in {
        "ভূল": "ভুল",
        "ভূলটি": "ভুলটি",
        "ভূলগুলো": "ভুলগুলো",
        "পুরুস্কার": "পুরস্কার",
        "পুরষ্কার": "পুরস্কার",
        "পরিক্ষা": "পরীক্ষা",
        "পরিক্ষার": "পরীক্ষার",
        "পরিক্ষায়": "পরীক্ষায়",
        "শারিরীক": "শারীরিক",
        "শারিরিক": "শারীরিক",
        "সহযোগীতা": "সহযোগিতা",
        "সহযোগীতায়": "সহযোগিতায়",
        "প্রতিযোগীতা": "প্রতিযোগিতা",
        "প্রতিযোগীতায়": "প্রতিযোগিতায়",
        "দূর্ঘটনা": "দুর্ঘটনা",
        "দূর্ঘটনায়": "দুর্ঘটনায়",
        "কার্য্যালয়": "কার্যালয়",
        "কার্য্যালয়ে": "কার্যালয়ে",
        "ইতিমধ্যে": "ইতোমধ্যে",
        "সান্তনা": "সান্ত্বনা",
        "মুহুর্ত": "মুহূর্ত",
        "মুহুর্তে": "মুহূর্তে",
        "মূহুর্ত": "মুহূর্ত",
        "মূর্হুত": "মুহূর্ত",
        "শ্রদ্ধাঞ্জলী": "শ্রদ্ধাঞ্জলি",
        "অঞ্জলী": "অঞ্জলি",
        "গীতাঞ্জলী": "গীতাঞ্জলি",
        "পুস্পাঞ্জলী": "পুষ্পাঞ্জলি",
        "পুষ্পাঞ্জলী": "পুষ্পাঞ্জলি",
        "প্রানী": "প্রাণী",
        "প্রানীজগৎ": "প্রাণিজগৎ",
        "প্রানীবিদ্যা": "প্রাণিবিদ্যা",
        "প্রান": "প্রাণ",
        "মনযোগ": "মনোযোগ",
        "মনযোগী": "মনোযোগী",
        "অধ্যায়ন": "অধ্যয়ন",
        "অধ্যায়নরত": "অধ্যয়নরত",
        "আকাংখা": "আকাঙ্ক্ষা",
        "আকাঙ্খা": "আকাঙ্ক্ষা",
        "উদ্দ্যেশ্য": "উদ্দেশ্য",
        "উদ্দ্যেশ্যে": "উদ্দেশ্যে",
        "কথপোকথন": "কথোপকথন",
        "দুরাবস্থা": "দুরবস্থা",
        "নিরব": "নীরব",
        "নিরবতা": "নীরবতা",
        "নিরোগী": "নীরোগ",
        "পূনরায়": "পুনরায়",
        "মরিচীকা": "মরীচিকা",
        "শিরচ্ছেদ": "শিরশ্ছেদ",
        "সমীচিন": "সমীচীন",
        "সমিচীন": "সমীচীন",
        "সৌজন্যতা": "সৌজন্য",
        "স্বাক্ষরতা": "সাক্ষরতা",
        "সমিপেষু": "সমীপেষু",
        "উপরোক্ত": "উপর্যুক্ত",
        "ঐক্যমত": "ঐকমত্য",
        "ঐক্যমত্য": "ঐকমত্য",
        "স্বস্ত্রীক": "সস্ত্রীক",
        "স্ববান্ধব": "সবান্ধব",
        "আবিস্কার": "আবিষ্কার",
        "পরিস্কার": "পরিষ্কার",
        "তিরষ্কার": "তিরস্কার",
        "নমষ্কার": "নমস্কার",
        "মনোকষ্ট": "মনঃকষ্ট",
        "মনকষ্ট": "মনঃকষ্ট",
        "বাংলাদেশী": "বাংলাদেশি",
        "বিদেশী": "বিদেশি",
        "চাকুরী": "চাকরি",
        "চাকুরীজীবী": "চাকরিজীবী",
        "জানুয়ারী": "জানুয়ারি",
        "ফেব্রুয়ারী": "ফেব্রুয়ারি",
        "লাইব্রেরী": "লাইব্রেরি",
        "ফার্মেসী": "ফার্মেসি",
        "একাডেমী": "একাডেমি",
        "ডিগ্রী": "ডিগ্রি",
        "রেজিস্ট্রারী": "রেজিস্ট্রারি",
        "প্রাইমারী": "প্রাইমারি",
        "সেকেন্ডারী": "সেকেন্ডারি",
        "অতিথী": "অতিথি",
        "জরুরী": "জরুরি",
        "বিতরন": "বিতরণ",
        "কারন": "কারণ",
        "অকারন": "অকারণ",
        "সাধারন": "সাধারণ",
        "অসাধারন": "অসাধারণ",
        "ব্যাকরন": "ব্যাকরণ",
        "নির্মান": "নির্মাণ",
        "গুরুত্বপূর্ন": "গুরুত্বপূর্ণ",
        "সম্পূর্ন": "সম্পূর্ণ",
        "অসম্পূর্ন": "অসম্পূর্ণ",
        "পরিপূর্ন": "পরিপূর্ণ",
        "উচ্চারন": "উচ্চারণ",
        "কল্যান": "কল্যাণ",
        "পরিমান": "পরিমাণ",
        "প্রমান": "প্রমাণ",
        "প্রমানিত": "প্রমাণিত",
        "গ্রহন": "গ্রহণ",
        "বর্ননা": "বর্ণনা",
        "বর্ন": "বর্ণ",
        "স্বর্ন": "স্বর্ণ",
        "কর্ন": "কর্ণ",
        "পূর্ন": "পূর্ণ",
        "অনুসরন": "অনুসরণ",
        "আচরন": "আচরণ",
        "উদাহরন": "উদাহরণ",
        "জাগরন": "জাগরণ",
        "নিরূপন": "নিরূপণ",
        "নিয়ন্ত্রন": "নিয়ন্ত্রণ",
        "সংরক্ষন": "সংরক্ষণ",
        "সমর্পন": "সমর্পণ",
        "স্মরন": "স্মরণ",
        "তামায়": "তোমায়",
    }.items()
}

# Strict orthographic equivalence groups (ONLY true spelling confusions, NEVER base consonant swaps like জ/চ)
STRICT_ORTHOGRAPHIC_TABLE = str.maketrans({
    "ী": "ি",
    "ূ": "ু",
    "ণ": "ন",
    "ষ": "শ",
    "স": "শ",
    "ড়": "র",
    "ঢ়": "র",
    "ৎ": "ত",
    "ঙ": "ং",
    "ৈ": "ে",
    "ৌ": "ো",
})


def phonetic_key(word: str) -> str:
    """Return a strictly orthographic-normalized skeleton of a Bengali word (preserves base consonants)."""
    s = word.translate(STRICT_ORTHOGRAPHIC_TABLE)
    return s.replace("\u200c", "")


def levenshtein_distance(s1: str, s2: str, max_dist: int = 1) -> int:
    """Compute Levenshtein edit distance between s1 and s2 with early exit if > max_dist."""
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if abs(len1 - len2) > max_dist:
        return max_dist + 1

    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len1 + 1))
    for j in range(1, len2 + 1):
        ch2 = s2[j - 1]
        curr_row = [j] + [0] * len1
        row_min = j
        for i in range(1, len1 + 1):
            cost = 0 if s1[i - 1] == ch2 else 1
            val = min(
                prev_row[i] + 1,        # deletion
                curr_row[i - 1] + 1,    # insertion
                prev_row[i - 1] + cost  # substitution
            )
            curr_row[i] = val
            if val < row_min:
                row_min = val
        if row_min > max_dist:
            return max_dist + 1
        prev_row = curr_row

    return prev_row[len1]


class OfflineSpellChecker:
    """Conservative local Bengali spell checker with suffix stemming, Islamic vocab, and strict edit-distance-1 threshold."""

    _shared_word_set: Optional[Set[str]] = None
    _shared_word_rank: Optional[Dict[str, int]] = None
    _shared_phonetic_index: Optional[Dict[str, List[str]]] = None

    def __init__(self, dict_path: Optional[str] = None):
        self.dict_path = dict_path or self._resolve_default_dict_path()
        self.word_set: Set[str] = set()
        self.word_rank: Dict[str, int] = {}
        self._phonetic_index: Dict[str, List[str]] = defaultdict(list)
        self._suggestion_cache: Dict[str, List[str]] = {}
        self._load_dictionary()

    @staticmethod
    def _resolve_default_dict_path() -> str:
        path = get_asset_path(os.path.join("dict", "bangla_words.txt"))
        if os.path.exists(path):
            return path
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(base, "assets", "dict", "bangla_words.txt")

    def _load_dictionary(self) -> None:
        """Load bangla_words.txt into an in-memory set and build orthographic skeleton index."""
        default_path = self._resolve_default_dict_path()
        if (
            self.dict_path == default_path
            and OfflineSpellChecker._shared_word_set is not None
            and OfflineSpellChecker._shared_word_rank is not None
            and OfflineSpellChecker._shared_phonetic_index is not None
        ):
            self.word_set = OfflineSpellChecker._shared_word_set
            self.word_rank = OfflineSpellChecker._shared_word_rank
            self._phonetic_index = OfflineSpellChecker._shared_phonetic_index
            return

        t0 = time.perf_counter()
        word_set: Set[str] = set(ISLAMIC_AND_CULTURAL_VOCAB)
        word_rank: Dict[str, int] = {w: idx for idx, w in enumerate(ISLAMIC_AND_CULTURAL_VOCAB)}
        phonetic_index: Dict[str, List[str]] = defaultdict(list)

        if os.path.exists(self.dict_path):
            with open(self.dict_path, "r", encoding="utf-8") as f:
                for rank, line in enumerate(f):
                    w = normalize_bangla_word(line)
                    if not w:
                        continue
                    if w not in word_set:
                        word_set.add(w)
                        word_rank[w] = rank

                    if rank < 80000:
                        pkey = phonetic_key(w)
                        if w not in phonetic_index[pkey] and len(phonetic_index[pkey]) < 6:
                            phonetic_index[pkey].append(w)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.info(
            "Loaded %d Bengali words into offline dictionary in %.1f ms from %s",
            len(word_set), elapsed_ms, self.dict_path
        )

        self.word_set = word_set
        self.word_rank = word_rank
        self._phonetic_index = phonetic_index

        if self.dict_path == default_path and word_set:
            OfflineSpellChecker._shared_word_set = word_set
            OfflineSpellChecker._shared_word_rank = word_rank
            OfflineSpellChecker._shared_phonetic_index = phonetic_index

    def is_root_valid(self, stem: str) -> bool:
        """Check if stem is present directly in the dictionary or cultural vocabulary."""
        if not stem:
            return False
        s = normalize_bangla_word(stem)
        if s in DIRECT_CORRECTIONS:
            return False
        # If this stem itself has a sub-stem in DIRECT_CORRECTIONS, it's invalid
        for suf in MORPH_SUFFIXES:
            if s.endswith(suf) and len(s) - len(suf) >= 3:
                inner_stem = s[:-len(suf)]
                if inner_stem in DIRECT_CORRECTIONS:
                    return False
        if s in self.word_set or s in ISLAMIC_AND_CULTURAL_VOCAB:
            return True
        if is_arabic_word(s, s) or is_foreign_word(s, s):
            return True
        return False

    def decompose_word(self, word: str) -> Tuple[str, str]:
        """Decompose an inflected word into (stem, suffix).

        1. Check if the word matches a suffix where the stem is known to be in DIRECT_CORRECTIONS
           (e.g. 'লাইব্রেরী' in 'লাইব্রেরীর'). If so, extract (stem, suffix).
        2. Check if the whole word directly exists in the dictionary and is valid. If yes, return (word, "").
        3. Otherwise, scan for matching trailing suffixes from MORPH_SUFFIXES (only if remaining stem length >= 3).
        4. Extract stem and suffix. If no match, return (word, "").
        """
        w = normalize_bangla_word(word)
        if not w:
            return ("", "")

        # Check for matching suffix where the stem is in DIRECT_CORRECTIONS
        for suf in MORPH_SUFFIXES:
            if w.endswith(suf):
                stem = w[:-len(suf)]
                if len(stem) >= 3 and stem in DIRECT_CORRECTIONS:
                    return (stem, suf)

        # Check if the whole word directly exists in the dictionary
        if self.is_root_valid(w):
            return (w, "")

        for suf in MORPH_SUFFIXES:
            if w.endswith(suf):
                stem = w[:-len(suf)]
                if len(stem) >= 3:
                    return (stem, suf)

        return (w, "")

    def suggest_root(self, stem: str) -> List[str]:
        """Find the closest valid dictionary suggestion for an invalid stem (Edit Distance <= 1)."""
        s = normalize_bangla_word(stem)
        if not s:
            return []

        # 1. Direct standard correction mapping
        if s in DIRECT_CORRECTIONS:
            return [DIRECT_CORRECTIONS[s]]

        # 2. Check trailing ী -> ি or ি -> ী conversion
        # e.g., লাইব্রেরী -> লাইব্রেরি, একাডেমি, শ্রেণি
        if s.endswith("ী"):
            cand = s[:-1] + "ি"
            if self.is_root_valid(cand):
                return [cand]
        elif s.endswith("ি"):
            cand = s[:-1] + "ী"
            if self.is_root_valid(cand):
                return [cand]

        # 3. Check conservative orthographic index (Edit distance == 1 AND identical phonetic skeleton)
        s_pkey = phonetic_key(s)
        candidates = self._phonetic_index.get(s_pkey, [])
        scored: List[Tuple[int, str]] = []
        for cand in candidates:
            if cand == s or len(cand) != len(s):
                continue
            if levenshtein_distance(s, cand, max_dist=1) == 1:
                rank = self.word_rank.get(cand, 999999)
                scored.append((rank, cand))

        scored.sort(key=lambda item: item[0])
        return [cand for _, cand in scored]

    def is_valid_word(self, word: str) -> bool:
        """O(1) membership check with Morphological Stemming & Suffix Handling (বিভক্তি/প্রত্যয়)."""
        if not word:
            return True
        w = normalize_bangla_word(word)
        if not w or not PURE_BANGLA_WORD_RE.match(w):
            return True
        if BANGLA_DIGITS_RE.match(w) or len(w) <= 1:
            return True

        # Explicitly flag known unambiguous misspellings
        if w in DIRECT_CORRECTIONS:
            return False

        # 1. Direct O(1) dictionary or Islamic/Arabic/Foreign vocabulary check
        if self.is_root_valid(w):
            return True

        # 2. Morphological Decomposition:
        stem, suf = self.decompose_word(w)
        if suf:
            # Step A: Check if stem is already a valid dictionary word
            if stem in DIRECT_CORRECTIONS:
                return False
            if self.is_root_valid(stem):
                return True
            # Handle stem ending in आ-কার + 'র'/'য়'/'তে' where root has no আ-কার or vice versa
            if suf in ("র", "য়", "তে", "কে") and stem.endswith("া") and len(stem) >= 3:
                bare_stem = stem[:-1]
                if self.is_root_valid(bare_stem):
                    return True

        # Fallback check for shorter words with stem len >= 2 (e.g. বইখানা, মা-কে, ইত্যাদি)
        for suf in INFLECTION_SUFFIXES:
            if w.endswith(suf) and len(w) - len(suf) >= 2:
                short_stem = w[:-len(suf)]
                if short_stem in DIRECT_CORRECTIONS:
                    return False
                if self.is_root_valid(short_stem):
                    return True

        return False

    def suggest(self, word: str, max_suggestions: int = 5) -> List[str]:
        """Generate high-confidence suggestions using Morphological Stemming & Re-inflection.

        1. Suffix Stripping & Extraction via decompose_word(word).
        2. Root Correction & Re-inflection:
           - Step A: If stem is already valid, word is valid -> []
           - Step B: If stem is invalid, find closest valid suggestion for stem.
           - Step C: Re-attach original suffix to corrected stem:
                     Corrected Root + Original Suffix (e.g. 'লাইব্রেরি' + 'র' = 'লাইব্রেরির').
           - Add this recombined form as primary suggestion.
        3. Safeguards:
           - Never drops case endings / suffixes.
           - Conservative edit-distance-1 threshold; preserves root meaning.
        """
        w = normalize_bangla_word(word)
        if not w or self.is_valid_word(w):
            return []

        if w in self._suggestion_cache:
            return self._suggestion_cache[w][:max_suggestions]

        # 1. Instant direct correction table for whole word
        if w in DIRECT_CORRECTIONS:
            corr = DIRECT_CORRECTIONS[w]
            self._suggestion_cache[w] = [corr]
            return [corr]

        # 2. Morphological Stemming & Re-inflection Engine
        stem, suf = self.decompose_word(w)
        if suf:
            # Step A: If stem is already a valid dictionary word, keep original word unchanged
            if self.is_root_valid(stem):
                self._suggestion_cache[w] = []
                return []

            # Step B: If stem is invalid, find closest valid dictionary suggestion for stem
            root_suggestions = self.suggest_root(stem)

            # Step C: Re-attach the original suffix to the corrected stem
            recombined_suggestions: List[str] = []
            for corr_stem in root_suggestions:
                recombined = corr_stem + suf
                if recombined not in recombined_suggestions:
                    recombined_suggestions.append(recombined)

            if recombined_suggestions:
                self._suggestion_cache[w] = recombined_suggestions[:max_suggestions]
                return recombined_suggestions[:max_suggestions]

        # Fallback to checking other suffixes in INFLECTION_SUFFIXES if decompose_word had len < 3 or didn't match
        for alt_suf in INFLECTION_SUFFIXES:
            if w.endswith(alt_suf) and len(w) - len(alt_suf) >= 2:
                short_stem = w[:-len(alt_suf)]
                if short_stem in DIRECT_CORRECTIONS:
                    corr = DIRECT_CORRECTIONS[short_stem] + alt_suf
                    self._suggestion_cache[w] = [corr]
                    return [corr]

        # 3. Whole-word conservative orthographic match (Edit Distance == 1 AND identical phonetic skeleton)
        pkey = phonetic_key(w)
        candidates = self._phonetic_index.get(pkey, [])
        scored: List[Tuple[int, str]] = []
        for cand in candidates:
            if cand == w or len(cand) != len(w):
                continue
            dist = levenshtein_distance(w, cand, max_dist=1)
            if dist == 1:
                rank = self.word_rank.get(cand, 999999)
                scored.append((rank, cand))

        scored.sort(key=lambda item: item[0])
        results: List[str] = [c for _, c in scored]
        self._suggestion_cache[w] = results[:max_suggestions]
        return results[:max_suggestions]

    def correct_word(self, word: str) -> str:
        """Return a high-confidence corrected word if available; when in doubt, leave original word untouched."""
        if self.is_valid_word(word):
            return word
        suggestions = self.suggest(word, max_suggestions=1)
        if suggestions:
            return suggestions[0]
        # Leave unrecognized words untouched rather than forcing a false replacement
        return word

    def get_unrecognized_words(self, text: str) -> List[str]:
        """Return list of unrecognized/potential typo words that have no high-confidence replacement."""
        if not text or not text.strip():
            return []
        working = normalize_bangla_word(convert_bijoy_to_unicode(text) if is_bijoy_text(text) else text)
        unrecognized: List[str] = []
        for tok in BANGLA_TOKEN_PATTERN.findall(working):
            if PURE_BANGLA_WORD_RE.match(tok) and not self.is_valid_word(tok):
                if not self.suggest(tok, max_suggestions=1) and tok not in unrecognized:
                    unrecognized.append(tok)
        return unrecognized

    def proofread_text(self, text: str) -> str:
        """Proofread full Bengali text 100% offline with conservative replacement:
        1. Auto-detects and converts Bijoy (ANSI) to Unicode if needed.
        2. Validates words with Bengali suffix stemming and Islamic/cultural vocabulary.
        3. Applies only high-confidence orthographic corrections (never distorts valid or inflected words).
        4. Applies Bangladesh Gazetteer location corrections when Thana/Upazila context is present.
        """
        if not text or not text.strip():
            return text

        working = text
        if is_bijoy_text(working):
            working = convert_bijoy_to_unicode(working)

        working = normalize_bangla_word(working)

        tokens = BANGLA_TOKEN_PATTERN.findall(working)
        corrected_tokens: List[str] = []
        for tok in tokens:
            if PURE_BANGLA_WORD_RE.match(tok):
                corrected_tokens.append(self.correct_word(tok))
            else:
                corrected_tokens.append(tok)

        result = "".join(corrected_tokens)
        result = apply_gazetteer_corrections(working, result)
        return result


def decompose_word(word: str, checker: Optional[OfflineSpellChecker] = None) -> Tuple[str, str]:
    """Module-level helper to decompose an inflected word into (stem, suffix)."""
    chk = checker or OfflineSpellChecker()
    return chk.decompose_word(word)

