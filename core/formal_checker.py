"""Formal compliance: page limits, template contamination (parameterized)."""
from typing import Dict


def check_formal(
    spans: Dict,
    full_text: str,
    proposal_cap: int = 10,
    cv_cap: int = 5,
    severe_overflow_factor: float = 1.5,
    template_sensitivity: float = 0.5,
) -> Dict:
    """Check page limits + template contamination.
    
    Parameters:
      proposal_cap, cv_cap: expected max pages per section
      severe_overflow_factor: multiplier above which we hard-FAIL
        (e.g., 1.5 → proposal>15p or cv>7.5p triggers FAIL)
      template_sensitivity: 0.0 = ignore, 1.0 = strict
    
    Codex #2 + #3 fix: hard caps in segmenter prevent runaway segments,
    so equal-to-cap is normal. Hard FAIL only on severe overflow.
    """
    issues = []
    warnings = []
    
    proposal_pages = spans.get("proposal", {}).get("page_count", 0)
    cv_pages = spans.get("cv", {}).get("page_count", 0)
    
    if not spans.get("proposal", {}).get("found"):
        warnings.append("Proposal section boundaries not detected")
    elif proposal_pages > proposal_cap:
        warnings.append(f"Proposal segment = {proposal_pages}p (>{proposal_cap}) — possible overflow")
    
    if not spans.get("cv", {}).get("found"):
        warnings.append("CV section boundaries not detected")
    elif cv_pages > cv_cap:
        warnings.append(f"CV segment = {cv_pages}p (>{cv_cap}) — possible overflow")
    
    # Template contamination — sensitivity-controlled
    template_markers_strict = [
        "[insert", "<placeholder>", "lorem ipsum", "to be completed",
        "tbd", "[your text here]", "delete this section"
    ]
    template_markers_loose = ["[insert", "<placeholder>", "lorem ipsum"]
    
    if template_sensitivity >= 0.7:
        markers = template_markers_strict
    elif template_sensitivity >= 0.3:
        markers = template_markers_loose
    else:
        markers = []
    
    contamination = [m for m in markers if m in full_text.lower()]
    if contamination:
        warnings.append(f"Template residue: {contamination}")
    
    # Hard FAIL only on severe overflow
    severe_proposal = proposal_cap * severe_overflow_factor
    severe_cv = cv_cap * severe_overflow_factor
    
    if proposal_pages > severe_proposal or cv_pages > severe_cv:
        issues.append(f"Severe page-limit overflow (proposal>{severe_proposal:.0f}p or cv>{severe_cv:.0f}p) — segmentation likely failed")
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
        "warnings": warnings,
        "params_used": {
            "proposal_cap": proposal_cap,
            "cv_cap": cv_cap,
            "severe_overflow_factor": severe_overflow_factor,
            "template_sensitivity": template_sensitivity,
        }
    }
