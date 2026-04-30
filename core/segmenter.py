"""Section segmentation: Proposal / CV / Ethics."""
import re
from typing import Dict, List, Tuple


PROPOSAL_MARKERS = [
    r"research\s+proposal", r"project\s+description", r"scientific\s+proposal",
    r"objectives?\b", r"methodology", r"work\s*plan"
]
CV_MARKERS = [
    r"curriculum\s+vitae", r"\bcv\b", r"academic\s+cv",
    r"education\b", r"professional\s+experience", r"publications?\b"
]
ETHICS_MARKERS = [
    r"ethics\s+(self.?assessment|declaration)", r"security\s+(scrutiny|issues)",
    r"data\s+management\s+plan", r"gender\s+dimension"
]


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


def segment_pages(pages: List[Dict]) -> Dict[str, Dict]:
    """Compute page spans for each section."""
    starts = find_section_starts(pages)
    total = len(pages)
    
    ordered = sorted(
        [(k, v) for k, v in starts.items() if v is not None],
        key=lambda x: x[1]
    )
    
    spans = {}
    for idx, (name, start) in enumerate(ordered):
        if idx + 1 < len(ordered):
            end = ordered[idx + 1][1] - 1
        else:
            end = total - 1
        spans[name] = {
            "start_page": start + 1,
            "end_page": end + 1,
            "page_count": end - start + 1,
            "found": True
        }
    
    for sec in ["proposal", "cv", "ethics"]:
        if sec not in spans:
            spans[sec] = {"start_page": None, "end_page": None, "page_count": 0, "found": False}
    
    return spans
