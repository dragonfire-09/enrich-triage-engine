"""Mobility timeline reconstruction (Turkey months in last N years)."""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


TURKEY_TOKENS = [
    "turkey", "turkiye", "türkiye", "tr,",
    "istanbul", "ankara", "izmir", "bursa", "antalya",
    "gaziantep", "konya", "kayseri", "eskisehir", "trabzon",
    "bogazici", "metu", "odtu", "itu", "bilkent", "koc university", "sabanci"
]

DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4})"
    r"\s*(?:-|–|to|until|present|current|now)\s*"
    r"(\d{1,2}[/\.\-]?\d{0,2}[/\.\-]?\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\b\d{4}|present|current|now)",
    re.IGNORECASE
)


def parse_mobility(cv_text: str, reference_date: datetime, lookback_years: int = 3) -> Dict:
    """Estimate months spent in Turkey within lookback window."""
    from dateutil import parser as dp
    
    if not cv_text.strip():
        return {
            "turkey_months": None,
            "confidence": "none",
            "evidence": "INSUFFICIENT_EVIDENCE",
            "status": "DOUBT"
        }
    
    window_start = reference_date - timedelta(days=365 * lookback_years)
    lines = cv_text.split("\n")
    turkey_intervals = []
    evidence_snippets = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        is_turkey = any(tok in line_lower for tok in TURKEY_TOKENS)
        if not is_turkey:
            continue
        
        context = " ".join(lines[max(0, i-1):min(len(lines), i+2)])
        match = DATE_RANGE_PATTERN.search(context)
        if not match:
            continue
        
        try:
            start_str = match.group(1)
            end_str = match.group(2)
            start = dp.parse(start_str, fuzzy=True, default=datetime(2000, 1, 1))
            if end_str.lower() in ["present", "current", "now"]:
                end = reference_date
            else:
                end = dp.parse(end_str, fuzzy=True, default=datetime(2000, 12, 31))
            
            start = max(start, window_start)
            end = min(end, reference_date)
            if start < end:
                turkey_intervals.append((start, end))
                evidence_snippets.append(context[:150].strip())
        except Exception:
            continue
    
    if not turkey_intervals:
        return {
            "turkey_months": 0,
            "confidence": "low",
            "evidence": "No Turkey-linked dated entries detected in CV",
            "status": "DOUBT"
        }
    
    turkey_intervals.sort()
    merged = [turkey_intervals[0]]
    for s, e in turkey_intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    
    total_days = sum((e - s).days for s, e in merged)
    months = round(total_days / 30.44, 1)
    
    return {
        "turkey_months": months,
        "confidence": "medium" if len(merged) >= 2 else "low",
        "evidence": " | ".join(evidence_snippets[:3]),
        "status": "PASS" if months <= 12 else "DOUBT",
        "intervals": [(s.strftime("%Y-%m"), e.strftime("%Y-%m")) for s, e in merged]
    }
