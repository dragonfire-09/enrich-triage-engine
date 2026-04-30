"""Mobility timeline reconstruction.

v5 fixes:
  - Undated Turkey mentions → DOUBT but with manual review (not hard fail)
  - Excludes more boilerplate Country/Institution lines that are address-only
  - Side signals stay informational
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


TURKEY_TOKENS = [
    "turkey", "turkiye", "türkiye", "tr,", "(tr)", "türkiye'de", "turkiye'de",
    "istanbul", "ankara", "izmir", "bursa", "antalya",
    "gaziantep", "konya", "kayseri", "eskisehir", "eskişehir", "trabzon",
    "adana", "mersin", "samsun", "diyarbakir", "denizli", "miletus",
    "middle east technical", "metu ", "metu,", "metu.", "odtu", "odtü", "günam", "gunam",
    "bogazici", "boğaziçi", "bosphorus university",
    "istanbul technical", "itu ", "itü", "itu,",
    "bilkent", "koc university", "koç university", "sabanci", "sabancı",
    "hacettepe", "ankara university", "istanbul university",
    "ege university", "gazi university", "yildiz technical", "yıldız teknik",
    "marmara university", "anadolu university", "atılım", "atilim",
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

# Lines that mention Turkey but are NOT mobility signals
EXCLUDE_PATTERNS = [
    re.compile(r"nationalit(?:y|ies)\s*[:\-]", re.IGNORECASE),
    re.compile(r"citizenship\s*[:\-]", re.IGNORECASE),
    re.compile(r"passport\s*[:\-]", re.IGNORECASE),
    re.compile(r"country\s+of\s+(?:birth|origin)\s*[:\-]", re.IGNORECASE),
    re.compile(r"place\s+of\s+birth\s*[:\-]", re.IGNORECASE),
    re.compile(r"^country\s*[:\-]", re.IGNORECASE),
    re.compile(r"^institution\s*[:\-]", re.IGNORECASE),
    re.compile(r"project\s+title\s*[:\-]", re.IGNORECASE),
    re.compile(r"acronym\s*[:\-]", re.IGNORECASE),
    re.compile(r"keywords?\s*[:\-]", re.IGNORECASE),
    re.compile(r"abstract\s*[:\-]", re.IGNORECASE),
]

NATIONALITY_PATTERN = re.compile(r"nationalit(?:y|ies)\s*[:\-]\s*([^\n]*)", re.IGNORECASE)
SECONDMENT_PATTERN = re.compile(r"secondment\s+institution\s*[:\-]?[^\n]*", re.IGNORECASE)


def _has_turkey_signal(text: str) -> bool:
    t = text.lower()
    return any(tok in t for tok in TURKEY_TOKENS)


def _is_excluded_line(line: str) -> bool:
    return any(p.search(line.strip()) for p in EXCLUDE_PATTERNS)


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
    lines = text.split("\n")
    intervals = []
    evidence = []
    raw_lines = []
    
    for i, line in enumerate(lines):
        if _is_excluded_line(line):
            continue
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


def _collect_side_signals(full_text: str) -> List[str]:
    signals = []
    if not full_text:
        return signals
    nat = NATIONALITY_PATTERN.search(full_text)
    if nat and _has_turkey_signal(nat.group(1)):
        signals.append(f"Nationality includes Turkey: {nat.group(1).strip()[:80]}")
    sec = SECONDMENT_PATTERN.search(full_text)
    if sec and _has_turkey_signal(sec.group(0)):
        signals.append(f"Secondment in TR: {sec.group(0)[:100]}")
    return signals


def parse_mobility(cv_text: str, reference_date: datetime, lookback_years: int = 3, full_text: str = "") -> Dict:
    """Estimate Turkey months. Falls back to full_text if CV is sparse.
    
    v5: undated Turkey mentions → soft DOUBT (manual review),
        nationality alone → PASS,
        truly empty CV → INSUFFICIENT_EVIDENCE.
    """
    window_start = reference_date - timedelta(days=365 * lookback_years)
    cv_text = cv_text or ""
    cv_meaningful = len(cv_text.strip()) > 200
    
    intervals, evidence, raw_lines = _scan_intervals(cv_text, reference_date, window_start) if cv_meaningful else ([], [], [])
    fallback_used = False
    
    if not intervals and full_text:
        intervals_full, evidence_full, raw_full = _scan_intervals(full_text, reference_date, window_start)
        if intervals_full:
            intervals = intervals_full
            evidence = evidence_full
            raw_lines = raw_full
            fallback_used = True
        else:
            raw_lines = list(set(raw_lines + raw_full))
    
    side_signals = _collect_side_signals(full_text)
    
    if not cv_meaningful and not intervals and not raw_lines:
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
        if raw_lines:
            return {
                "turkey_months": None,
                "confidence": "low",
                "evidence": f"Turkey-linked but undated: {' | '.join(raw_lines[:3])}",
                "status": "DOUBT",
                "intervals": [],
                "side_signals": side_signals,
                "fallback_used": fallback_used,
                "needs_ocr": False
            }
        return {
            "turkey_months": 0,
            "confidence": "medium",
            "evidence": f"No Turkey-based work/education in last {lookback_years}y. Side signals: " + (" | ".join(side_signals) if side_signals else "none"),
            "status": "PASS",
            "intervals": [],
            "side_signals": side_signals,
            "fallback_used": fallback_used,
            "needs_ocr": False
        }
    
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
