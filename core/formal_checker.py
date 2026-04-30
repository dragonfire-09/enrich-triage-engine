"""Formal compliance: page limits, template contamination."""
from typing import Dict


def check_formal(spans: Dict, full_text: str) -> Dict:
    """Check page limits + template contamination signals."""
    issues = []
    warnings = []
    
    proposal_pages = spans.get("proposal", {}).get("page_count", 0)
    cv_pages = spans.get("cv", {}).get("page_count", 0)
    
    if not spans.get("proposal", {}).get("found"):
        warnings.append("Proposal section boundaries not detected")
    elif proposal_pages > 10:
        warnings.append(f"Proposal segment = {proposal_pages}p (>10) — verify boundary")
    
    if not spans.get("cv", {}).get("found"):
        warnings.append("CV section boundaries not detected")
    elif cv_pages > 5:
        warnings.append(f"CV segment = {cv_pages}p (>5) — verify boundary")
    
    template_markers = ["[insert", "<placeholder>", "lorem ipsum", "tbd", "to be completed"]
    contamination = [m for m in template_markers if m in full_text.lower()]
    if contamination:
        warnings.append(f"Template residue detected: {contamination}")
    
    if proposal_pages > 12 or cv_pages > 7:
        issues.append("Hard page-limit violation likely")
        decision = "FAIL"
    elif warnings:
        decision = "DOUBT"
    else:
        decision = "PASS"
    
    return {
        "decision": decision,
        "proposal_pages": proposal_pages,
        "cv_pages": cv_pages,
        "issues": issues,
        "warnings": warnings
    }
