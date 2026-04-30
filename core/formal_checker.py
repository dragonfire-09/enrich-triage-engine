"""Formal compliance: page limits, template contamination."""
from typing import Dict


def check_formal(spans: Dict, full_text: str) -> Dict:
    """Check page limits + template contamination signals.
    
    Note: After segmenter v2 introduces hard caps (10 for proposal, 5 for CV),
    we should NOT auto-fail just because page_count == cap.
    Only fail if we have STRONG evidence of overflow.
    """
    issues = []
    warnings = []
    
    proposal_pages = spans.get("proposal", {}).get("page_count", 0)
    cv_pages = spans.get("cv", {}).get("page_count", 0)
    
    # Soft warnings (not failures)
    if not spans.get("proposal", {}).get("found"):
        warnings.append("Proposal section boundaries not detected")
    elif proposal_pages > 10:
        warnings.append(f"Proposal segment = {proposal_pages}p (>10) — possible overflow")
    
    if not spans.get("cv", {}).get("found"):
        warnings.append("CV section boundaries not detected")
    elif cv_pages > 5:
        warnings.append(f"CV segment = {cv_pages}p (>5) — possible overflow")
    
    # Template contamination
    template_markers = ["[insert", "<placeholder>", "lorem ipsum", "to be completed"]
    contamination = [m for m in template_markers if m in full_text.lower()]
    if contamination:
        warnings.append(f"Template residue detected: {contamination}")
    
    # Hard fail ONLY if extreme overflow (segmenter clearly missed boundary)
    # With hard cap of 10/5, segments equal to cap are NORMAL, not failures
    if proposal_pages > 15 or cv_pages > 10:
        issues.append("Severe page-limit overflow — segmentation likely failed")
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
