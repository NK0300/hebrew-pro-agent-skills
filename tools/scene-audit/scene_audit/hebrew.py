"""Hebrew-aware term matching for the production document.

Before the audit says "the spec does not mention X", it searches for X with and
without niqqud, with final letters folded, with or without matres lectionis
(full and defective spelling), and with geresh variants.
"""

from __future__ import annotations

import re
import unicodedata

NIQQUD = re.compile(r"[֑-ׇ]")
FINALS = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
GERESH = str.maketrans({"׳": "'", "״": '"', "`": "'", "’": "'", "‘": "'", "“": '"', "”": '"'})
HEBREW_LETTER = re.compile(r"[א-ת]")


def strip_niqqud(text: str) -> str:
    return NIQQUD.sub("", unicodedata.normalize("NFC", text))


def normalize(text: str) -> str:
    """Lowercase, no niqqud, final letters folded, quotes unified."""
    text = strip_niqqud(text).translate(FINALS).translate(GERESH)
    return text.lower()


def skeleton(text: str) -> str:
    """normalize() and drop vav/yod inside words, so full and defective spelling meet."""
    text = normalize(text)

    def fold(word: re.Match[str]) -> str:
        w = word.group(0)
        if len(w) <= 2:
            return w
        inner = re.sub(r"[וי]", "", w[1:-1])
        return w[0] + inner + w[-1]

    return re.sub(r"[א-ת]+", fold, text)


PREFIXES = ("ו", "ה", "ב", "כ", "ל", "מ", "ש")


def variants(term: str) -> list[str]:
    term = term.strip()
    base = normalize(term)
    out = {base, skeleton(term)}
    if HEBREW_LETTER.search(base):
        # Allow a single-letter prefix in the text (ו, ה, ב...). The regex handles it.
        out.add(base.replace("'", ""))
    return sorted(v for v in out if v)


def search(term: str, lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, line) pairs that contain the term in any variant."""
    norm_term = normalize(term)
    skel_term = skeleton(term)
    prefix = "(?:[" + "".join(PREFIXES) + "]{0,2})"
    patterns = []
    for t in {norm_term, skel_term}:
        if not t:
            continue
        escaped = re.escape(t)
        if HEBREW_LETTER.search(t):
            patterns.append(re.compile(r"(?<![א-ת])" + prefix + escaped))
        else:
            patterns.append(re.compile(escaped))
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(lines, start=1):
        norm = normalize(line)
        skel = skeleton(line)
        if any(p.search(norm) or p.search(skel) for p in patterns):
            hits.append((number, line))
    return hits
