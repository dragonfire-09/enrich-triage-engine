"""Application metadata extraction (regex-based)."""
import re
from typing import Dict


METADATA_PATTERNS = {
    "applicant_name": [
        re.compile(r"applicant(?:\s+name)?\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
        re.compile(r"name\s+and\s+surname\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
    ],
    "project_title": [
        re.compile(r"project\s+title\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
    ],
    "application_id": [
        re.compile(r"application\s+id\s*[:\-]\s*([a-f0-9\-]{8,})", re.IGNORECASE),
        re.compile(r"\b([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\b", re.IGNORECASE),
    ],
    "nationality": [
        re.compile(r"nationalit(?:y|ies)\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
    ],
    "current_institution": [
        re.compile(r"current\s+institution\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
        re.compile(r"host\s+institution\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
        re.compile(r"organi[sz]ation\s*[:\-]\s*([^•|\n]+)", re.IGNORECASE),
    ],
}

ETHICS_PATTERNS = [
    re.compile(r"ethics\s+(?:self.?assessment|declaration|table|issues)", re.IGNORECASE),
    re.compile(r"security\s+(?:scrutiny|self.?assessment|issues)", re.IGNORECASE),
]

ENGLISH_WORDS = set([
    "the", "and", "of", "to", "in", "is", "that", "for", "with", "this",
    "research", "project", "proposal", "objective", "method", "analysis",
    "results", "study", "data", "approach", "scientific", "between",
    "however", "therefore", "furthermore", "moreover",
])

# UUID pattern for trailing-ID cleanup (used only on non-ID fields)
_UUID_TAIL_RE = re.compile(
    r"\s*(?:application\s*id\s*[:\-]?\s*)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*$",
    re.IGNORECASE,
)


def _clean_value(raw: str, field_name: str = "") -> str:
    """Strip bullets, pipes, trailing 'Application ID', and UUIDs from name-like fields.
    
    field_name: when 'application_id', UUID stripping is SKIPPED (UUID IS the value).
    """
    if not raw:
        return raw
    
    # Cut at common end-of-name separators
    for sep in ["•", "|", "  Application ID", "  application id", "\tApplication ID"]:
        idx = raw.find(sep)
        if idx > 0:
            raw = raw[:idx]
            break
    
    # Only strip trailing UUIDs for non-ID fields
    if field_name != "application_id":
        raw = _UUID_TAIL_RE.sub("", raw)
    
    return raw.strip(" \t\n\r:-•|")


def _first_match(text: str, patterns, field_name: str = "") -> str:
    for pat in patterns:
        m = pat.search(text)
        if m:
            value = m.group(1).strip()
            value = re.split(r"\s{2,}|\n", value)[0].strip()
            value = value.rstrip(".,;:")
            value = _clean_value(value, field_name=field_name)
            if value and len(value) < 200:
                return value
    return "INSUFFICIENT_EVIDENCE"


def extract_metadata(full_text: str) -> Dict:
    """Extract structured metadata from full PDF text."""
    if not full_text:
        return {k: "INSUFFICIENT_EVIDENCE" for k in METADATA_PATTERNS.keys()} | {
            "ethics_tables_present": "INSUFFICIENT_EVIDENCE",
            "english_signal": "INSUFFICIENT_EVIDENCE",
        }
    
    out = {}
    for field, patterns in METADATA_PATTERNS.items():
        out[field] = _first_match(full_text, patterns, field_name=field)
    
    # Ethics tables
    ethics_hits = sum(1 for p in ETHICS_PATTERNS if p.search(full_text))
    if ethics_hits >= 2:
        out["ethics_tables_present"] = "YES"
    elif ethics_hits == 1:
        out["ethics_tables_present"] = "PARTIAL"
    else:
        out["ethics_tables_present"] = "NO"
    
    # English signal
    sample = full_text[:5000].lower()
    words = re.findall(r"\b[a-z]+\b", sample)
    if len(words) >= 50:
        eng_count = sum(1 for w in words if w in ENGLISH_WORDS)
        ratio = eng_count / len(words)
        if ratio > 0.08:
            out["english_signal"] = "YES"
        elif ratio > 0.03:
            out["english_signal"] = "WEAK"
        else:
            out["english_signal"] = "NO"
    else:
        out["english_signal"] = "INSUFFICIENT_EVIDENCE"
    
    return out
