"""PhD date extraction with multi-format + keyword tolerance."""
import re
from datetime import datetime
from typing import Dict, Optional, List
from dateutil import parser as date_parser


PHD_KEYWORDS = [
    "phd", "ph.d", "doctorate", "doctoral degree",
    "defense", "defence", "viva", "thesis defense",
    "successfully defended", "awarded",
    "doktora", "savunma", "tez savunma"
]

DATE_PATTERNS = [
    r"\b(\d{1,2})[/\.\-](\d{1,2})[/\.\-](\d{4})\b",
    r"\b(\d{4})[/\.\-](\d{1,2})[/\.\-](\d{1,2})\b",
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{4})\b",
    r"\b(Ocak|Subat|Mart|Nisan|Mayis|Haziran|Temmuz|Agustos|Eylul|Ekim|Kasim|Aralik)\s+(\d{4})\b",
    r"\b(\d{4})\b",
]


def extract_phd_evidence(full_text: str, deadline: datetime) -> Dict:
    """Find PhD date and decide eligibility."""
    lines = full_text.split("\n")
    candidates = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in PHD_KEYWORDS):
            context = " ".join(lines[i:min(i+3, len(lines))])
            for pattern in DATE_PATTERNS:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(0)
                        parsed = date_parser.parse(date_str, fuzzy=True, default=datetime(2000, 1, 1))
                        candidates.append({
                            "date": parsed,
                            "quote": context[:200].strip(),
                            "line_idx": i
                        })
                        break
                    except Exception:
                        continue
    
    if not candidates:
        return {
            "found": False,
            "date": None,
            "evidence_quote": "INSUFFICIENT_EVIDENCE",
            "eligible": None,
            "confidence": "none"
        }
    
    best = max(candidates, key=lambda c: c["date"])
    
    eligible = best["date"] <= deadline
    confidence = "high" if len(candidates) >= 2 else "medium"
    
    return {
        "found": True,
        "date": best["date"],
        "evidence_quote": best["quote"],
        "eligible": eligible,
        "confidence": confidence,
        "all_candidates": [(c["date"].strftime("%Y-%m-%d"), c["quote"][:80]) for c in candidates]
    }
