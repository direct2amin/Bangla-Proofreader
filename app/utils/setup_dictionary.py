"""Automated Offline Dictionary Builder for Bangla Proofreader.

Downloads open-source Bengali dictionary dumps (LibreOffice bn_BD.dic, BengaliWordList,
and FrequencyWords bn_full), merges official Bangladesh Gazetteer locations, normalizes
to standard precomposed Bengali Unicode, filters out common & phonetic misspellings,
and saves ~135,000-140,000 standard Bengali words into `assets/dict/bangla_words.txt`.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path
from typing import Dict, List, Set

BANGLA_WORD_RE = re.compile(r"^[\u0980-\u09FF\u200c]+$")

PHONETIC_NORMALIZATION_TABLE = str.maketrans({
    "ী": "ি",
    "ূ": "ু",
    "ণ": "ন",
    "ষ": "শ",
    "স": "শ",
    "ড়": "র",
    "ঢ়": "র",
    "ৎ": "ত",
    "ঙ": "ং",
})


def normalize_word(w: str) -> str:
    """Normalize a Bengali word to NFC while keeping ড়, ঢ়, য় as single precomposed codepoints."""
    s = unicodedata.normalize("NFC", w.strip())
    return (
        s.replace("\u09a1\u09bc", "\u09dc")
        .replace("\u09a2\u09bc", "\u09dd")
        .replace("\u09af\u09bc", "\u09df")
    )


def phonetic_skeleton(w: str) -> str:
    return w.translate(PHONETIC_NORMALIZATION_TABLE)


# Common Bengali misspellings that MUST NOT be in the valid dictionary set
KNOWN_MISSPELLINGS: Set[str] = {
    normalize_word(x) for x in [
        "ভূল", "ভূলটি", "ভূলগুলো",
        "পুরুস্কার", "পুরষ্কার",
        "পরিক্ষা", "পরিক্ষার", "পরিক্ষায়",
        "শারিরীক", "শারিরিক",
        "সহযোগীতা", "সহযোগীতায়",
        "প্রতিযোগীতা", "প্রতিযোগীতায়",
        "দূর্ঘটনা", "দূর্ঘটনায়",
        "কার্য্যালয়", "কার্য্যালয়ে",
        "ইতিমধ্যে",
        "সান্তনা",
        "মুহুর্ত", "মুহুর্তে", "মুহুর্তের", "মুহুর্তেই", "মুহুর্তকে", "মুহুর্তগুলো",
        "মুহুর্থ", "মুহুর্থে", "মুহুর্থের", "মুহুর্থেই", "মুহুর্থকে", "মুহুর্থগুলো",
        "মূহুর্ত", "মূহুর্তে", "মূহুর্তের", "মূহুর্তেই",
        "মূহুর্থ", "মূহুর্থে", "মূহুর্থের", "মূহুর্থেই",
        "মূর্হুত", "মূর্হুতে", "মূর্হুতের", "মুহূর্ত্থ",
        "উজ্জল", "উজ্জলে", "উজ্জলের", "উজ্জলতা", "উজ্জলভাবে",
        "উচ্ছাস", "উচ্ছাসে", "উচ্ছাসের", "উচ্ছাসিত",
        "দ্বন্দ", "দ্বন্দে", "দ্বন্দের", "দ্বন্ধ", "দ্বন্ধে", "দ্বন্ধের",
        "কষ্ঠ", "কষ্ঠের", "কষ্ঠদায়ক", "কষ্ঠকর",
        "স্বার্ত", "স্বার্তে", "স্বার্তের", "স্বার্তপর", "স্বার্তপরতা",
        "মিষ্ঠি", "মিষ্ঠির", "মিষ্ঠিতে",
        "সৃষ্ঠি", "সৃষ্ঠির", "সৃষ্ঠিতে", "সৃষ্ঠিকর্তা",
        "দৃষ্ঠি", "দৃষ্ঠির", "দৃষ্ঠিতে", "দৃষ্ঠিকোণ", "দৃষ্ঠিগোচর",
        "সন্তুষ্ঠ", "তুষ্ঠ", "রুষ্ঠ", "শ্রেষ্ট", "শ্রেষ্টত্ব", "জ্যৈষ্ট",
        "ঘনিষ্ট", "ঘনিষ্টতা", "ঘনিষ্টভাবে", "কনিষ্ট",
        "পৃষ্টা", "পৃষ্টায়", "পৃষ্টার", "নিষ্টা", "নিষ্টাবান",
        "পিপিলিকা", "পিপিলীকা", "পিপীলীকা",
        "কৌতুহল", "কৌতুহলে", "কৌতুহলী", "কৌতুহলোদ্দীপক",
        "প্রতিকুল", "প্রতিকুলে", "প্রতিকুলতা", "অনুকুল", "অনুকুলে",
        "দূরবস্থা", "দূরাবস্থা", "দুরর্ঘটনা", "দুরর্ঘটনায়",
        "দুরত্ব", "দুরবর্তী", "দুরদর্শী", "দুরবীক্ষণ",
        "আইনজীবি", "বুদ্ধিজীবি", "শ্রমজীবি", "পেশাজীবি", "কৃষিজীবি", "মৎস্যজীবি",
        "দায়ীত্ব", "দায়ীত্বশীল", "স্থায়ীত্ম",
        "পোষাক", "মাষ্টার", "পোষ্ট", "পোষ্টের", "পোষ্টে", "পোষ্টাফিস",
        "ষ্টেশন", "ষ্টেশনের", "রেজিষ্ট্রেশন", "ইনষ্টিটিউট", "রেস্তোরা",
        "শ্রদ্ধাঞ্জলী", "অঞ্জলী", "গীতাঞ্জলী", "পুস্পাঞ্জলী", "পুষ্পাঞ্জলী",
        "প্রানী", "প্রানীজগৎ", "প্রানীবিদ্যা", "প্রান",
        "মনযোগ", "মনযোগী",
        "অধ্যায়ন", "অধ্যায়নরত",
        "আকাংখা", "আকাঙ্খা",
        "উদ্দ্যেশ্য", "উদ্দ্যেশ্যে",
        "কথপোকথন",
        "দুরাবস্থা",
        "নিরব", "নিরবতা",
        "নিরোগী",
        "পূনরায়", "পুনরায়ই",
        "মরিচীকা",
        "শিরচ্ছেদ",
        "সমীচিন", "সমিচীন",
        "সৌজন্যতা",
        "স্বাক্ষরতা",
        "সমিপেষু", "সমীপেষু",
        "উপরোক্ত",
        "ঐক্যমত", "ঐক্যমত্য",
        "স্বস্ত্রীক",
        "স্ববান্ধব",
        "অশ্রুজল",
        "আবিস্কার",
        "পরিস্কার",
        "তিরষ্কার",
        "নমষ্কার",
        "মনোকষ্ট", "মনকষ্ট",
        "বাংলাদেশী", "বিদেশী",
        "চাকুরী", "চাকুরীজীবী",
        "জানুয়ারী", "ফেব্রুয়ারী",
        "লাইব্রেরী", "ফার্মেসী", "একাডেমী", "ডিগ্রী",
        "রেজিস্ট্রারী", "প্রাইমারী", "সেকেন্ডারী",
        "অতিথী", "জরুরী",
        "আশির্বাদ", "আশির্বাদে", "আশির্বাদের",
        "নূন্যতম", "নূণ্যতম", "ন্যুনতম",
        "ইদানিং", "ইদানিংকার",
        "সারাজিবন", "সারাজিবনে", "সারাজিবনের",
        "আকষ্মিক", "আকষ্মিকতা", "আকষ্মিকভাবে",
        "বিতরন", "কারন", "অকারন", "সাধারন", "অসাধারন", "ব্যাকরন",
        "নির্মান", "গুরুত্বপূর্ন", "সম্পূর্ন", "অসম্পূর্ন", "পরিপূর্ন",
        "উচ্চারন", "কল্যান", "পরিমান", "প্রমান", "প্রমানিত",
        "গ্রহন", "বর্ননা", "বর্ন", "স্বর্ন", "কর্ন", "পূর্ন",
        "অনুসরন", "আচরন", "উদাহরন", "জাগরন", "ধারণ", "নিরূপন",
        "নিয়ন্ত্রন", "সংরক্ষন", "সমর্পন", "স্মরন", "হরিণ",
        "তামায়",
    ]
} - {normalize_word("ধারণ"), normalize_word("হরিণ")}

# Essential standard Bengali words that must always be present at top priority
ESSENTIAL_VALID_WORDS: List[str] = [
    normalize_word(x) for x in [
        "ভুল", "ভুলটি", "ভুলগুলো", "পুরস্কার", "পরীক্ষা", "পরীক্ষার", "পরীক্ষায়",
        "শারীরিক", "সহযোগিতা", "সহযোগিতায়", "প্রতিযোগিতা", "প্রতিযোগিতায়",
        "দুর্ঘটনা", "দুর্ঘটনায়", "কার্যালয়", "কার্যালয়ে", "ইতোমধ্যে", "সান্ত্বনা",
        "মুহূর্ত", "মুহূর্তে", "মুহূর্তের", "মুহূর্তেই", "মুহূর্তগুলো", "মুহূর্তটি", "মুহূর্তটা",
        "উজ্জ্বল", "উজ্জ্বলে", "উজ্জ্বলের", "উজ্জ্বলতা", "উজ্জ্বলভাবে",
        "উচ্ছ্বাস", "উচ্ছ্বাসে", "উচ্ছ্বাসের", "উচ্ছ্বসিত",
        "দ্বন্দ্ব", "দ্বন্দ্বে", "দ্বন্দ্বের",
        "কষ্ট", "কষ্টের", "কষ্টদায়ক", "কষ্টকর",
        "স্বার্থ", "স্বার্থে", "স্বার্থের", "স্বার্থপর", "স্বার্থপরতা",
        "মিষ্টি", "মিষ্টির", "মিষ্টিতে",
        "সৃষ্টি", "সৃষ্টির", "সৃষ্টিতে", "সৃষ্টিকর্তা",
        "দৃষ্টি", "দৃষ্টির", "দৃষ্টিতে", "দৃষ্টিকোণ", "দৃষ্টিগোচর",
        "সন্তুষ্ট", "তুষ্ট", "রুষ্ট", "শ্রেষ্ঠ", "শ্রেষ্ঠত্ব", "জ্যৈষ্ঠ",
        "ঘনিষ্ঠ", "ঘনিষ্ঠতা", "ঘনিষ্ঠভাবে", "কনিষ্ঠ",
        "পৃষ্ঠা", "পৃষ্ঠায়", "পৃষ্ঠার", "নিষ্ঠা", "নিষ্ঠাবান",
        "পিপীলিকা", "কৌতূহল", "কৌতূহলে", "কৌতূহলী", "কৌতূহলোদ্দীপক",
        "প্রতিকূল", "প্রতিকূলে", "প্রতিকূলতা", "অনুকূল", "অনুকূলে",
        "দূরত্ব", "দূরবর্তী", "দূরদর্শী", "দূরবীক্ষণ",
        "আইনজীবী", "বুদ্ধিজীবী", "শ্রমজীবী", "পেশাজীবী", "কৃষিজীবী", "মৎস্যজীবী",
        "দায়িত্ব", "দায়িত্বশীল", "স্থায়িত্ব",
        "পোশাক", "মাস্টার", "পোস্ট", "পোস্টের", "পোস্টে", "পোস্টঅফিস",
        "স্টেশন", "স্টেশনের", "রেজিস্ট্রেশন", "ইনস্টিটিউট", "রেস্তোরাঁ",
        "শ্রদ্ধাঞ্জলি", "অঞ্জলি", "গীতাঞ্জলি", "পুষ্পাঞ্জলি",
        "প্রাণী", "প্রাণিজগৎ", "প্রাণিবিদ্যা", "প্রাণ", "মনোযোগ", "মনোযোগী",
        "অধ্যয়ন", "অধ্যয়নরত", "আকাঙ্ক্ষা", "উদ্দেশ্য", "উদ্দেশ্যে",
        "কথোপকথন", "দুরবস্থা", "নীরব", "নীরবতা", "নীরোগ", "পুনরায়",
        "মরীচিকা", "শিরশ্ছেদ", "সমীচীন", "সৌজন্য", "সাক্ষরতা",
        "উপর্যুক্ত", "ঐকমত্য", "সস্ত্রীক", "সবান্ধব", "আবিষ্কার",
        "পরিষ্কার", "তিরস্কার", "নমস্কার", "মনঃকষ্ট", "বাংলাদেশি", "বিদেশি",
        "চাকরি", "চাকরিজীবী", "জানুয়ারি", "ফেব্রুয়ারি", "লাইব্রেরি",
        "আশীর্বাদ", "আশীর্বাদে", "আশীর্বাদের", "ন্যূনতম", "ইদানীং", "সারাজীবন", "সারাজীবনে", "সারাজীবনের", "আকস্মিক",
        "ফার্মেসি", "একাডেমি", "ডিগ্রি", "প্রাইমারি", "সেকেন্ডারি", "অতিথি", "জরুরি",
        "বিতরণ", "কারণ", "অকারণ", "সাধারণ", "অসাধারণ", "ব্যাকরণ",
        "নির্মাণ", "গুরুত্বপূর্ণ", "সম্পূর্ণ", "অসম্পূর্ণ", "পরিপূর্ণ",
        "উচ্চারণ", "কল্যাণ", "পরিমাণ", "প্রমাণ", "প্রমাণিত",
        "গ্রহণ", "বর্ণনা", "বর্ণ", "স্বর্ণ", "কর্ণ", "পূর্ণ",
        "অনুসরণ", "আচরণ", "উদাহরণ", "জাগরণ", "ধারণ", "নিরূপণ",
        "নিয়ন্ত্রণ", "সংরক্ষণ", "সমর্পণ", "স্মরণ", "হরিণ",
        "বাংলা", "বাংলাদেশ", "আমার", "সোনার", "আমি", "তোমায়", "ভালোবাসি",
        "প্রুফরিডার", "বানান", "সংশোধন", "শুদ্ধিকরণ", "অনুষ্ঠান",
        # Islamic, Arabic-Persian, and Cultural Vocabulary & Inflections
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
        "শাবান", "রজব", "মহররম", "শাওয়াল", "জিলহজ", "জিলকদ", "বলে-কয়ে",
    ]
]


def fetch_url_text(url: str) -> str:
    """Download UTF-8 text from URL with a browser User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def build_bangla_wordlist(target_count: int = 140000) -> List[str]:
    """Download open-source Bengali wordlists and build a clean ~140k wordlist."""
    freq_map: Dict[str, int] = {}

    # 1. FrequencyWords (bn_full.txt) for frequency ranking
    print("Downloading FrequencyWords (bn_full.txt)...")
    try:
        freq_text = fetch_url_text(
            "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/bn/bn_full.txt"
        )
        for line in freq_text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                w = normalize_word(parts[0])
                if BANGLA_WORD_RE.match(w) and len(w) >= 2:
                    try:
                        freq_map[w] = max(freq_map.get(w, 0), int(parts[1]))
                    except ValueError:
                        freq_map[w] = max(freq_map.get(w, 0), 1)
    except Exception as e:
        print(f"Warning: Could not fetch FrequencyWords: {e}")

    # 2. LibreOffice / Hunspell bn_BD.dic (Curated standard Bangla dictionary)
    curated_words: Set[str] = set()
    print("Downloading LibreOffice bn_BD.dic...")
    try:
        dic_text = fetch_url_text(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/bn_BD/bn_BD.dic"
        )
        for idx, line in enumerate(dic_text.splitlines()):
            if idx == 0 and line.strip().isdigit():
                continue
            w = normalize_word(line.split("/")[0].split("\t")[0])
            if BANGLA_WORD_RE.match(w) and len(w) >= 2:
                curated_words.add(w)
    except Exception as e:
        print(f"Warning: Could not fetch bn_BD.dic: {e}")

    # 3. MinhasKamal BengaliWordList_439.txt (Comprehensive Bengali lexicon)
    lexicon_words: Set[str] = set()
    print("Downloading MinhasKamal BengaliWordList_439.txt...")
    try:
        lex_text = fetch_url_text(
            "https://raw.githubusercontent.com/MinhasKamal/BengaliDictionary/master/BengaliWordList_439.txt"
        )
        for line in lex_text.splitlines():
            w = normalize_word(line)
            if BANGLA_WORD_RE.match(w) and 2 <= len(w) <= 22:
                lexicon_words.add(w)
    except Exception as e:
        print(f"Warning: Could not fetch BengaliWordList_439.txt: {e}")

    # 4. Merge Bangladesh Gazetteer locations from assets/bd_locations.json
    base_dir = Path(__file__).resolve().parent.parent.parent
    loc_file = base_dir / "assets" / "bd_locations.json"
    location_words: Set[str] = set()
    if loc_file.exists():
        try:
            with open(loc_file, "r", encoding="utf-8") as f:
                loc_data = json.load(f)
            for item in loc_data.get("districts", []):
                for token in str(item).split():
                    w = normalize_word(token)
                    if BANGLA_WORD_RE.match(w) and len(w) >= 2:
                        location_words.add(w)
            for thana_name, info in loc_data.get("thanas", {}).items():
                for token in str(thana_name).split():
                    w = normalize_word(token)
                    if BANGLA_WORD_RE.match(w) and len(w) >= 2:
                        location_words.add(w)
                if isinstance(info, dict):
                    for key in ("unions", "post_offices", "villages"):
                        for item in info.get(key, []):
                            for token in str(item).split():
                                w = normalize_word(token)
                                if BANGLA_WORD_RE.match(w) and len(w) >= 2:
                                    location_words.add(w)
        except Exception as e:
            print(f"Warning: Could not read bd_locations.json: {e}")

    ordered_words: List[str] = []
    seen: Set[str] = set()
    curated_skeletons: Set[str] = set()

    def add_curated(w: str) -> None:
        if w and w not in seen and w not in KNOWN_MISSPELLINGS and BANGLA_WORD_RE.match(w):
            seen.add(w)
            curated_skeletons.add(phonetic_skeleton(w))
            ordered_words.append(w)

    for w in ESSENTIAL_VALID_WORDS:
        add_curated(w)

    for w in sorted(location_words, key=lambda x: (-freq_map.get(x, 0), x)):
        add_curated(w)

    for w in sorted(curated_words, key=lambda x: (-freq_map.get(x, 0), x)):
        add_curated(w)

    def add_uncurated(w: str) -> None:
        if not w or w in seen or w in KNOWN_MISSPELLINGS or not BANGLA_WORD_RE.match(w):
            return
        seen.add(w)
        ordered_words.append(w)

    freq_candidates = [
        w for w, count in sorted(freq_map.items(), key=lambda item: -item[1])
        if (w in lexicon_words or count >= 25)
    ]
    for w in freq_candidates:
        add_uncurated(w)
        if len(ordered_words) >= target_count:
            break

    if len(ordered_words) < target_count:
        remaining = sorted(
            lexicon_words - seen,
            key=lambda x: (-freq_map.get(x, 0), len(x), x)
        )
        for w in remaining:
            add_uncurated(w)
            if len(ordered_words) >= target_count:
                break

    return ordered_words


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent.parent
    words = build_bangla_wordlist(target_count=140000)
    print(f"Compiled {len(words)} clean Bengali words.")

    target_paths = [
        base_dir / "assets" / "dict" / "bangla_words.txt",
        base_dir / "app" / "assets" / "dict" / "bangla_words.txt",
    ]
    content = "\n".join(words) + "\n"
    for path in target_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved {len(words)} words to {path} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
