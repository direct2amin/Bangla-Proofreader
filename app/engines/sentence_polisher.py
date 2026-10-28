"""Dedicated Sentence Polish Engine for Bangla Proofreader.

Analyzes Bengali sentence structure, removes redundant phrasing, fixes awkward syntax
and guruchandali dosh, and makes the prose natural, elegant, and professional
while strictly preserving native Arabic quotes, hadiths, and core meaning.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

from app.core.config import load_config

logger = logging.getLogger(__name__)

SENTENCE_POLISH_SYSTEM_PROMPT = """You are a professional Bengali stylistic editor and literary polisher.
The input text has already been spell-checked and is orthographically correct.
Your task is purely stylistic and structural enhancement:
1. Analyze the sentence structure, remove redundant phrasing, fix awkward syntax and গুরুচণ্ডালী দোষ (guruchandali dosh).
2. Make the prose natural, elegant, smooth, and professional without altering the author's core meaning or intent.
3. STRICT SAFEGUARD: DO NOT alter or modify any native Arabic quotes, Quranic verses, Hadith texts, or Islamic phrases.
4. Provide sentence-level suggestions clearly showing Original vs Polished version.

You MUST respond strictly in valid JSON format matching this JSON schema:
{
  "polished_text": "The full polished Bengali text with all refinements applied",
  "sentence_changes": [
    {
      "original": "The exact original sentence that was improved",
      "polished": "The improved, polished sentence",
      "reason": "Brief explanation in Bengali of what was refined (e.g. বাহুল্য বর্জন, গুরুচণ্ডালী দোষ পরিহার, বা বাক্য গঠন সাবলীলকরণ)"
    }
  ]
}
Do not include markdown code fences or any conversational preface/postscript. Output only the pure JSON.
"""


@dataclass
class SentenceChange:
    change_id: int
    original: str
    polished: str
    reason: str
    is_accepted: bool = True


@dataclass
class SentencePolishResult:
    original_text: str
    full_polished_text: str
    changes: List[SentenceChange]


class SentencePolisher:
    """Dedicated AI engine for Bengali stylistic refinement and sentence polishing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or load_config().get("gemini_api_key", "")
        self.client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self) -> None:
        if not self.api_key or not genai:
            self.client = None
            return
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error("Failed to initialize Gemini Client for SentencePolisher: %s", e)
            self.client = None

    def polish_text(self, text: str) -> SentencePolishResult:
        """Execute sentence polish on pre-checked Bengali text."""
        if not text or not text.strip():
            return SentencePolishResult(original_text=text, full_polished_text=text, changes=[])

        config = load_config()
        self.api_key = config.get("gemini_api_key", self.api_key)
        if not self.client:
            self._init_client()

        if not self.client:
            raise RuntimeError("Gemini API Key is not configured. Please enter your API key in Settings.")

        model_name = config.get("gemini_model", "gemini-3.5-flash")
        candidate_models = [model_name, "gemini-2.5-flash", "gemini-3.8-flash-lite"]

        prompt = (
            f"Please stylistically polish and refine the following Bengali text:\n\n"
            f"<text_to_polish>\n{text}\n</text_to_polish>"
        )

        last_error = None
        for cand_model in candidate_models:
            try:
                gen_config = genai_types.GenerateContentConfig(
                    system_instruction=SENTENCE_POLISH_SYSTEM_PROMPT,
                    temperature=0.3,
                    response_mime_type="application/json",
                )
                response = self.client.models.generate_content(
                    model=cand_model,
                    contents=prompt,
                    config=gen_config,
                )
                raw_json = response.text.strip()
                if raw_json.startswith("```"):
                    lines = raw_json.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    raw_json = "\n".join(lines).strip()

                data = json.loads(raw_json)
                full_polished = data.get("polished_text", text)
                raw_changes = data.get("sentence_changes", [])

                changes: List[SentenceChange] = []
                for idx, c in enumerate(raw_changes, start=1):
                    orig_s = str(c.get("original", "")).strip()
                    pol_s = str(c.get("polished", "")).strip()
                    reason = str(c.get("reason", "বাক্য গঠন পরিমার্জন")).strip()
                    if orig_s and pol_s and orig_s != pol_s:
                        changes.append(
                            SentenceChange(
                                change_id=idx,
                                original=orig_s,
                                polished=pol_s,
                                reason=reason,
                                is_accepted=True,
                            )
                        )

                # Fallback sentence diffing if model returned full text without structured changes
                if not changes and full_polished and full_polished.strip() != text.strip():
                    changes = self._fallback_sentence_segmentation(text, full_polished)

                return SentencePolishResult(
                    original_text=text,
                    full_polished_text=full_polished,
                    changes=changes,
                )
            except Exception as e:
                logger.warning("Sentence polish attempt with %s failed: %s", cand_model, e)
                last_error = e

        raise RuntimeError(f"Sentence Polish failed: {last_error}")

    @staticmethod
    def _fallback_sentence_segmentation(orig: str, polished: str) -> List[SentenceChange]:
        """Heuristic sentence segmentation fallback when JSON list is empty."""
        sep = re.compile(r"([।!?\n]+)")
        orig_parts = [p.strip() for p in sep.split(orig) if p.strip() and not sep.match(p)]
        pol_parts = [p.strip() for p in sep.split(polished) if p.strip() and not sep.match(p)]

        changes: List[SentenceChange] = []
        for idx, (o, p) in enumerate(zip(orig_parts, pol_parts), start=1):
            if o != p:
                changes.append(
                    SentenceChange(
                        change_id=idx,
                        original=o,
                        polished=p,
                        reason="বাক্য গঠন ও সাবলীলতা পরিমার্জন",
                        is_accepted=True,
                    )
                )
        return changes
