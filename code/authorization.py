"""Deterministic request-intent checks for deletion authorization."""

import re


_DELETION_WORD = re.compile(
    r"\b(?:delet\w*|eras\w*|remov\w*|clos\w*|wip\w*|destroy\w*|forget\w*|"
    r"elimin\w*|borr\w*|suprim\w*|suppression|supprim\w*|effac\w*|"
    r"exclu\w*|fermer|cl[oô]tur\w*)\b|[削除消去閉鎖解約]|삭제",
    re.IGNORECASE,
)
_EXPLICIT_NEGATION = re.compile(
    r"\b(?:do\s+not|don't|dont|never)\s+(?:please\s+)?"
    r"(?:delete|erase|remove|close|wipe|destroy)\b|"
    r"\bwithout\s+(?:deleting|erasing|removing|closing)\b|"
    r"\bnot\s+(?:asking|requesting)\s+for\s+(?:an?\s+)?deletion\b",
    re.IGNORECASE,
)
_MARKETING_ONLY = re.compile(
    r"\bmarketing\b.{0,50}\b(?:only|opt[ -]?out|unsubscribe)\b|"
    r"\b(?:only|opt[ -]?out|unsubscribe)\b.{0,50}\bmarketing\b",
    re.IGNORECASE,
)


def authorizes_deletion(request_text: str) -> bool:
    """Return whether the request asks for deletion of an account or its data."""
    text = (request_text or "").casefold().replace("’", "'").replace("‘", "'")
    prior_deletion_check = re.search(
        r"\b(?:account|profile)\b.{0,80}\b(?:gone|removed|deleted|erased)\b|"
        r"\b(?:gone|removed|deleted|erased)\b.{0,80}\b(?:account|profile)\b",
        text,
    )
    if not text or (not _DELETION_WORD.search(text) and not prior_deletion_check):
        return False
    if _EXPLICIT_NEGATION.search(text):
        return False
    # A marketing preference change alone does not authorize account erasure.
    if _MARKETING_ONLY.search(text) and not re.search(
        r"\baccount\b.{0,60}\b(?:delet\w*|eras\w*|clos\w*)\b|"
        r"\b(?:delet\w*|eras\w*|clos\w*)\b.{0,60}\baccount\b",
        text,
    ):
        return False
    return True
