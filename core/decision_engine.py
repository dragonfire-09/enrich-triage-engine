"""Final decision aggregation."""
from typing import Dict


def aggregate_decision(phd: Dict, formal: Dict, thematic: Dict, mobility: Dict) -> Dict:
    """Combine all layer decisions per system-prompt rules."""
    reasons = []
    
    # PhD eligibility (hard gate)
    if phd["found"] is False:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "primary_reason": "PhD date not extractable",
            "reasons": ["PhD date not found - manual review required"],
            "manual_review": True
        }
    if phd["eligible"] is False:
        return {
            "decision": "PHD_INELIGIBLE",
            "primary_reason": f"PhD/defense date {phd['date']} > deadline",
            "reasons": [phd["evidence_quote"]],
            "manual_review": False
        }
    
    # Collect non-blocking signals
    if formal["decision"] == "FAIL":
        reasons.append("Formal: " + "; ".join(formal["issues"]))
    if thematic["decision"] == "FAIL":
        reasons.append(f"Thematic FAIL (score={thematic['score']})")
    
    mob_status = mobility.get("status", "PASS")
    if mob_status == "INSUFFICIENT_EVIDENCE":
        reasons.append(f"Mobility INSUFFICIENT_EVIDENCE: {mobility.get('evidence','')}")
    elif mob_status == "DOUBT":
        reasons.append(f"Mobility DOUBT: {mobility.get('evidence','')}")
    
    # Priority order
    if any("Formal:" in r for r in reasons):
        return {"decision": "FAIL_FORMAL", "primary_reason": reasons[0], "reasons": reasons, "manual_review": False}
    if any("Thematic FAIL" in r for r in reasons):
        return {"decision": "FAIL_THEMATIC", "primary_reason": reasons[0], "reasons": reasons, "manual_review": True}
    if mob_status == "INSUFFICIENT_EVIDENCE":
        return {"decision": "INSUFFICIENT_EVIDENCE", "primary_reason": reasons[-1], "reasons": reasons, "manual_review": True}
    if mob_status == "DOUBT":
        return {"decision": "DOUBT_MOBILITY", "primary_reason": reasons[-1], "reasons": reasons, "manual_review": True}
    
    return {"decision": "PASS", "primary_reason": "All layers passed", "reasons": [], "manual_review": False}
