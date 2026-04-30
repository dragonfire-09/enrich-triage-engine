"""Section segmentation: Proposal / CV / Ethics — with hard page caps + boundary detection."""
import re
from typing import Dict, List, Tuple


PROPOSAL_MARKERS = [
    r"research\s+proposal", r"project\s+description", r"scientific\s+proposal",
    r"part\s*b\s*[-–]\s*", r"section\s+1", r"\b1\.?\s+excellence\b",
    r"objectives?\b", r"methodology", r"work\s*plan"
]

CV_MARKERS = [
    r"curriculum\s+vitae", r"\bcv\b", r"academic\s+cv",
    r"part\s*b\s*[-–]\s*cv", r"researcher\s+profile",
    r"\beducation\b", r"professional\s+experience"
]

ETHICS_MARKERS = [
    r"ethics\s+(self.?assessment|declaration|table|issues)",
    r"security\s+(scrutiny|issues|self.?assessment)",
    r"data\s+management\s+plan",
    r"gender\s+dimension"
]

# Boundary signals - things that strongly indicate END of proposal or CV
END_OF_PROPOSAL_SIGNALS = [
    r"^\s*references?\s*$",
    r"^\s*bibliography\s*$",
    r"^\s*annex(es)?\s*[:\-]?\s*$",
    r"^\s*appendix\s*[a-z0-9]?\s*$",
    r"curriculum\s+vitae",
    r"^\s*cv\s*$",
    r"part\s*b\s*[-–]\s*cv",
    r"ethics\s+self.?assessment",
    r"security\s+self.?assessment",
    r"declarations?\b",
]

END_OF_CV_SIGNALS = [
    r"ethics\s+self.?assessment",
    r"ethics\s+declaration",
    r"security\s+(scrutiny|self.?assessment)",
    r"data\s+management\s+plan",
    r"declarations?\b",
    r"^\s*annex(es)?\s*[:\-]?\s*$",
    r"^\s*appendix\s*[a-z0-9]?\s*$",
    r"list\s+of\s+publications",
    r"publications?\s+list",
]

# Hard caps - safety net per ENRICH-like rules
PROPOSAL_HARD_CAP = 10
CV_HARD_CAP = 5


def find_section_starts(pages: List[Dict]) -> Dict[str, int]:
    """Return {section: start_page_index} for each section."""
    starts = {"proposal": None, "cv": None, "ethics": None}
    
    for i, page in enumerate(pages):
        text_lower = page["text"].lower()
        
        if starts["proposal"] is None:
            if any(re.search(p, text_lower) for p in PROPOSAL_MARKERS):
                starts["proposal"] = i
        
        if starts["cv"] is None and (starts["proposal"] is None or i > starts["proposal"]):
            if any(re.search(p, text_lower) for p in CV_MARKERS):
                starts["cv"] = i
        
        if starts["ethics"] is None:
            if any(re.search(p, text_lower) for p in ETHICS_MARKERS):
                starts["ethics"] = i
    
    return starts


def find_boundary_after(pages: List[Dict], start: int, end_signals: List[str], hard_cap: int) -> int:
    """Find earliest boundary signal after `start`, capped at `hard_cap` pages.
    
    Returns the page index where the section ENDS (inclusive).
    """
    max_end = min(start + hard_cap - 1, len(pages) - 1)
    
    # Look for end signals strictly AFTER start page
    for i in range(start + 1, min(start + hard_cap + 3, len(pages))):
        text_lower = pages[i]["text"].lower()
        # Check if this page has an end-signal in its FIRST 200 chars (likely a header)
        first_chunk = text_lower[:300]
        if any(re.search(sig, first_chunk, re.MULTILINE) for sig in end_signals):
            return i - 1  # section ends on previous page
    
    return max_end


def segment_pages(pages: List[Dict]) -> Dict[str, Dict]:
    """Compute page spans for each section with hard caps + boundary detection.
    
    Strategy:
      1. Find section starts via markers
      2. For each section, find end via:
         a) explicit end-signal on subsequent pages, OR
         b) start of next known section, OR
         c) hard page cap (10 for proposal, 5 for CV)
    """
    starts = find_section_starts(pages)
    total = len(pages)
    spans = {}
    
    # ---- PROPOSAL ----
    if starts["proposal"] is not None:
        p_start = starts["proposal"]
        # Boundary candidates: CV start, Ethics start, end-signals, hard cap
        candidates = []
        if starts["cv"] is not None and starts["cv"] > p_start:
            candidates.append(starts["cv"] - 1)
        if starts["ethics"] is not None and starts["ethics"] > p_start:
            candidates.append(starts["ethics"] - 1)
        # End-signal scan
        sig_end = find_boundary_after(pages, p_start, END_OF_PROPOSAL_SIGNALS, PROPOSAL_HARD_CAP)
        candidates.append(sig_end)
        # Hard cap
        candidates.append(p_start + PROPOSAL_HARD_CAP - 1)
        candidates.append(total - 1)
        
        p_end = min(candidates)
        spans["proposal"] = {
            "start_page": p_start + 1,
            "end_page": p_end + 1,
            "page_count": p_end - p_start + 1,
            "found": True
        }
    else:
        spans["proposal"] = {"start_page": None, "end_page": None, "page_count": 0, "found": False}
    
    # ---- CV ----
    if starts["cv"] is not None:
        c_start = starts["cv"]
        candidates = []
        if starts["ethics"] is not None and starts["ethics"] > c_start:
            candidates.append(starts["ethics"] - 1)
        sig_end = find_boundary_after(pages, c_start, END_OF_CV_SIGNALS, CV_HARD_CAP)
        candidates.append(sig_end)
        candidates.append(c_start + CV_HARD_CAP - 1)
        candidates.append(total - 1)
        
        c_end = min(candidates)
        spans["cv"] = {
            "start_page": c_start + 1,
            "end_page": c_end + 1,
            "page_count": c_end - c_start + 1,
            "found": True
        }
    else:
        spans["cv"] = {"start_page": None, "end_page": None, "page_count": 0, "found": False}
    
    # ---- ETHICS ----
    if starts["ethics"] is not None:
        e_start = starts["ethics"]
        e_end = total - 1
        spans["ethics"] = {
            "start_page": e_start + 1,
            "end_page": e_end + 1,
            "page_count": e_end - e_start + 1,
            "found": True
        }
    else:
        spans["ethics"] = {"start_page": None, "end_page": None, "page_count": 0, "found": False}
    
    return spans
