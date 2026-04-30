"""Mobility timeline reconstruction — flexible country/location detection.

v3 fixes:
  - Falls back to full document text if CV section is sparse/empty
  - Detects 'Nationality: Turkey' and 'Secondment Institution' as side signals
  - Distinguishes INSUFFICIENT_EVIDENCE from DOUBT
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


TURKEY_TOKENS = [
    # Country names
    "turkey", "turkiye", "türkiye", "tr,", "(tr)", "türkiye'de", "turkiye'de",
    # Major cities
    "istanbul", "ankara", "izmir", "bursa", "antalya",
    "gaziantep", "konya", "kayseri", "eskisehir", "trabzon",
    "adana", "mersin", "samsun", "diyarbakir", "denizli",
    # Universities (full names + abbreviations)
    "middle east technical", "metu ", "metu,", "metu.", "odtu", "odtü", "günam", "gunam",
    "bogazici", "boğaziçi", "bosphorus university",
    "istanbul technical", "itu ", "itü", "itu,",
    "bilkent", "koc university", "koç university", "sabanci", "sabancı",
    "hacettepe", "ankara university", "istanbul university",
    "ege university", "gazi university", "yildiz technical", "yıldız teknik",
    "marmara university", "anadolu university",
    "tubitak", "tübitak",
]

DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4})"
    r"\s*(?:-|–|—|to|until|present|current|now)\s*"
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4}|present|current|now|ongoing)",
    re.IGNORECASE
)

SINGLE_DATE_PATTERN = re.compile(
    r"(?:since|from|as\s+of|starting)\s+(\d{4})|"
    r"\b(\d{4})\s*[-–]\s*(?:present|current|now|ongoing|today)",
    re.IGNORECASE
)

YEAR_PATTERN = re.compile(r"\b(19[89]\d|20\d{2})\b")

# Side signals — even without dates, these hint at Turkey involvement
NATIONALITY_PATTERN = re.compile(r"nationalit(?:y|ies)\s*[:\-]\s*(turkey|turkiye|türkiye|tr)\b", re.IGNORECASE)
SECONDMENT_PATTERN = re.compile(r"secondment\s+institution\s*[:\-]?[^\n]*", re.IGNORECASE)
HOST_INSTITUTION_PATTERN = re.compile(r"(?:host|current)\s+institution\s*[:\-]?[^\n]*", re.IGNORECASE)


def _has_turkey_signal(text: str) -> bool:
    t = text.lower()
    return any(tok in t for tok in TURKEY_TOKENS)


def _parse_date_loose(s: str, default_dt: datetime) -> Optional[datetime]:
    from dateutil import parser as dp
    try:
        return dp.parse(s, fuzzy=True, default=default_dt)
    except Exception:
        m = YEAR_PATTERN.search(s)
        if m:
            return datetime(int(m.group(1)), default_dt.month, default_dt.day)
        return None


def _scan_intervals(text: str, reference_date: datetime, window_start: datetime) -> Tuple[List, List, List]:
    """Scan a text body for Turkey-linked dated intervals."""
    lines = text.split("\n")
    intervals = []
    evidence = []
    raw_lines = []
    
    for i, line in enumerate(lines):
        if not _has_turkey_signal(line):
            continue
        raw_lines.append(line.strip()[:120])
        context = " ".join(lines[max(0, i-2):min(len(lines), i+3)])
        
        match = DATE_RANGE_PATTERN.search(context)
        if match:
            start_str, end_str = match.group(1), match.group(2)
            start = _parse_date_loose(start_str, datetime(2000, 1, 1))
            end = reference_date if end_str.lower() in ["present","current","now","ongoing"] else _parse_date_loose(end_str, datetime(2000, 12, 31))
            if start and end and start < end:
                start = max(start, window_start)
                end = min(end, reference_date)
                if start < end:
                    intervals.append((start, end))
                    evidence.append(f"[range] {context[:140].strip()}")
                    continue
        
        s_match = SINGLE_DATE_PATTERN.search(context)
        if s_match:
            year = s_match.group(1) or s_match.group(2)
            try:
                start = max(datetime(int(year), 1, 1), window_start)
                if start < reference_date:
                    intervals.append((start, reference_date))
                    evidence.append(f"[since] {context[:140].strip()}")
                    continue
            except Exception:
                pass
        
        years = sorted(set(int(y) for y in YEAR_PATTERN.findall(context)))
        if years:
            try:
                start = datetime(years[0], 1, 1)
                end = datetime(years[-1], 12, 31) if len(years) >= 2 else datetime(years[0], 12, 31)
                start = max(start, window_start)
                end = min(end, reference_date)
                if start < end:
                    intervals.append((start, end))
                    evidence.append(f"[years] {context[:140].strip()}")
            except Exception:
                pass
    
    return intervals, evidence, raw_lines


def parse_mobility(cv_text: str, reference_date: datetime, lookback_years: int = 3, full_text: str = "") -> Dict:
    """Estimate Turkey months. Falls back to full_text if CV is sparse.
    
    Returns INSUFFICIENT_EVIDENCE if CV is image-based / empty.
    """
    window_start = reference_date - timedelta(days=365 * lookback_years)
    
    # Step 1: try CV first
    cv_text = cv_text or ""
    cv_meaningful = len(cv_text.strip()) > 200  # need at least some real content
    
    intervals, evidence, raw_lines = _scan_intervals(cv_text, reference_date, window_start) if cv_meaningful else ([], [], [])
    fallback_used = False
    
    # Step 2: fallback to full text if CV yielded nothing
    if not intervals and full_text:
        intervals, evidence, raw_lines = _scan_intervals(full_text, reference_date, window_start)
        if intervals:
            fallback_used = True
    
    # Step 3: side signals (nationality, secondment) for context
    side_signals = []
    if full_text:
        if NATIONALITY_PATTERN.search(full_text):
            side_signals.append("Nationality: Turkey detected")
        sec = SECONDMENT_PATTERN.search(full_text)
        if sec and _has_turkey_signal(sec.group(0)):
            side_signals.append(f"Secondment in TR: {sec.group(0)[:100]}")
    
    # Step 4: handle empty CV case
    if not cv_meaningful and not intervals:
        return {
            "turkey_months": None,
            "confidence": "none",
            "evidence": "CV section appears image-based or empty — OCR may be required. " + (" | ".join(side_signals) if side_signals else ""),
            "status": "INSUFFICIENT_EVIDENCE",
            "intervals": [],
            "side_signals": side_signals,
            "fallback_used": fallback_used,
            "needs_ocr": True
        }
    
    if not intervals:
        return {
            "turkey_months": 0,
            "confidence": "low",
            "evidence": ("Turkey-linked but undated: " + " | ".join(raw_lines[:3])) if raw_lines else "No Turkey-linked dated entries found",
            "status": "DOUBT" if raw_lines or side_signals else "PASS",
            "intervals": [],
            "side_signals": side_signals,
            "fallback_used": fallback_used,
            "needs_ocr": False
        }
    
    # Merge intervals
    intervals.sort()
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    
    total_days = sum((e - s).days for s, e in merged)
    months = round(total_days / 30.44, 1)
    
    if months <= 12:
        status = "PASS"
    elif months <= 18:
        status = "DOUBT"
    else:
        status = "DOUBT"
    
    return {
        "turkey_months": months,
        "confidence": "medium" if fallback_used else ("high" if len(merged) >= 2 else "medium"),
        "evidence": " || ".join(evidence[:3]) + (" [fallback: full doc]" if fallback_used else ""),
        "status": status,
        "intervals": [(s.strftime("%Y-%m"), e.strftime("%Y-%m")) for s, e in merged],
        "side_signals": side_signals,
        "fallback_used": fallback_used,
        "needs_ocr": False
    }
