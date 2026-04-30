"""Mobility timeline reconstruction — flexible country/location detection.

Codex #5 fix: handle
  - "since YYYY" / single dates without ranges
  - city-based country inference (METU → Turkey)
  - free-text year mentions
  - overlapping roles
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


# Expanded Turkey tokens — institutions, cities, country names
TURKEY_TOKENS = [
    # Country names
    "turkey", "turkiye", "türkiye", "tr,", "(tr)",
    # Major cities
    "istanbul", "ankara", "izmir", "bursa", "antalya",
    "gaziantep", "konya", "kayseri", "eskisehir", "trabzon",
    "adana", "mersin", "samsun", "diyarbakir", "denizli",
    # Universities (full names + abbreviations)
    "middle east technical", "metu ", "metu,", "metu.", "odtu", "odtü",
    "bogazici", "boğaziçi", "bosphorus university",
    "istanbul technical", "itu ", "itü", "itu,",
    "bilkent", "koc university", "koç university", "sabanci", "sabancı",
    "hacettepe", "ankara university", "istanbul university",
    "ege university", "gazi university", "yildiz technical", "yıldız teknik",
    "marmara university", "anadolu university",
    "tubitak", "tübitak",
]

# Date range patterns (start - end)
DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4})"
    r"\s*(?:-|–|—|to|until|present|current|now)\s*"
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4}|present|current|now|ongoing)",
    re.IGNORECASE
)

# Single-date patterns (e.g., "since 2018", "from 2020", "2019-")
SINGLE_DATE_PATTERN = re.compile(
    r"(?:since|from|as\s+of|starting)\s+(\d{4})|"
    r"\b(\d{4})\s*[-–]\s*(?:present|current|now|ongoing|today)",
    re.IGNORECASE
)

# Standalone year for last-resort matching
YEAR_PATTERN = re.compile(r"\b(19[89]\d|20\d{2})\b")


def _has_turkey_signal(text: str) -> bool:
    """Case-insensitive check for any Turkey-linked token."""
    t = text.lower()
    return any(tok in t for tok in TURKEY_TOKENS)


def _parse_date_loose(s: str, default_dt: datetime) -> Optional[datetime]:
    """Try multiple parsers; return None if all fail."""
    from dateutil import parser as dp
    try:
        return dp.parse(s, fuzzy=True, default=default_dt)
    except Exception:
        # last resort: pick a year
        m = YEAR_PATTERN.search(s)
        if m:
            return datetime(int(m.group(1)), default_dt.month, default_dt.day)
        return None


def parse_mobility(cv_text: str, reference_date: datetime, lookback_years: int = 3) -> Dict:
    """Estimate months spent in Turkey within lookback window.
    
    Strategy:
      1. Scan each line for Turkey signal
      2. Around each Turkey hit, look for:
         a) explicit date range
         b) "since YYYY" / "YYYY - present"
         c) standalone years (year-only fallback)
      3. Merge overlapping intervals
      4. Compute months in lookback window
    """
    if not cv_text.strip():
        return {
            "turkey_months": None,
            "confidence": "none",
            "evidence": "INSUFFICIENT_EVIDENCE",
            "status": "DOUBT"
        }
    
    window_start = reference_date - timedelta(days=365 * lookback_years)
    lines = cv_text.split("\n")
    intervals: List[Tuple[datetime, datetime]] = []
    evidence_snippets: List[str] = []
    raw_turkey_lines: List[str] = []
    
    for i, line in enumerate(lines):
        if not _has_turkey_signal(line):
            continue
        
        raw_turkey_lines.append(line.strip()[:120])
        
        # widen context for date hunting
        context = " ".join(lines[max(0, i-2):min(len(lines), i+3)])
        
        # Try strategy 1: explicit date range
        match = DATE_RANGE_PATTERN.search(context)
        if match:
            start_str, end_str = match.group(1), match.group(2)
            start = _parse_date_loose(start_str, datetime(2000, 1, 1))
            if end_str.lower() in ["present", "current", "now", "ongoing"]:
                end = reference_date
            else:
                end = _parse_date_loose(end_str, datetime(2000, 12, 31))
            
            if start and end and start < end:
                start = max(start, window_start)
                end = min(end, reference_date)
                if start < end:
                    intervals.append((start, end))
                    evidence_snippets.append(f"[range] {context[:140].strip()}")
                    continue
        
        # Try strategy 2: "since YYYY" or "YYYY - present"
        s_match = SINGLE_DATE_PATTERN.search(context)
        if s_match:
            year = s_match.group(1) or s_match.group(2)
            try:
                start = datetime(int(year), 1, 1)
                end = reference_date
                start = max(start, window_start)
                if start < end:
                    intervals.append((start, end))
                    evidence_snippets.append(f"[since] {context[:140].strip()}")
                    continue
            except Exception:
                pass
        
        # Try strategy 3: any year mentioned near Turkey signal
        year_matches = YEAR_PATTERN.findall(context)
        if year_matches:
            years = sorted(set(int(y) for y in year_matches))
            try:
                if len(years) >= 2:
                    start = datetime(years[0], 1, 1)
                    end = datetime(years[-1], 12, 31)
                else:
                    start = datetime(years[0], 1, 1)
                    end = datetime(years[0], 12, 31)
                start = max(start, window_start)
                end = min(end, reference_date)
                if start < end:
                    intervals.append((start, end))
                    evidence_snippets.append(f"[years] {context[:140].strip()}")
            except Exception:
                pass
    
    if not intervals:
        # We saw Turkey signals but couldn't pin dates → low-confidence DOUBT
        if raw_turkey_lines:
            return {
                "turkey_months": None,
                "confidence": "low",
                "evidence": f"Turkey-linked but undated: {' | '.join(raw_turkey_lines[:3])}",
                "status": "DOUBT",
                "intervals": []
            }
        return {
            "turkey_months": 0,
            "confidence": "low",
            "evidence": "No Turkey-linked entries detected in CV",
            "status": "DOUBT",
            "intervals": []
        }
    
    # Merge overlapping
    intervals.sort()
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    
    total_days = sum((e - s).days for s, e in merged)
    months = round(total_days / 30.44, 1)
    
    # ENRICH-like rule: max 12 months in Turkey within last 3 years
    if months <= 12:
        status = "PASS"
    elif months <= 18:
        status = "DOUBT"
    else:
        status = "DOUBT"  # uncertain → DOUBT, never auto-FAIL per Codex note
    
    return {
        "turkey_months": months,
        "confidence": "high" if len(merged) >= 2 else "medium",
        "evidence": " || ".join(evidence_snippets[:3]),
        "status": status,
        "intervals": [(s.strftime("%Y-%m"), e.strftime("%Y-%m")) for s, e in merged]
    }
