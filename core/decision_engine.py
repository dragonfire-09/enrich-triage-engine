"""Final decision aggregation.

v3: Thematic FAIL is now rare — mostly DOUBT.
    Mobility undated mentions → DOUBT (manual review), not blocking.
"""
from typing import Dict


def aggregate_decision(phd: Dict, formal: Dict, thematic: Dict, mobility: Dict) -> Dict:
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
    
    if formal["decision"] == "FAIL":
        reasons.append("Formal: " + "; ".join(formal["issues"]))
    if thematic["decision"] == "FAIL":
        reasons.append(f"Thematic FAIL (score={thematic['score']})")
    
    mob_status = mobility.get("status", "PASS")
    th_status = thematic.get("decision", "PASS")
    
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
    
    # If thematic is DOUBT or mobility is DOUBT → DOUBT outcome with manual review
    if th_status == "DOUBT" or mob_status == "DOUBT":
        which = []
        if th_status == "DOUBT":
            which.append(f"Thematic DOUBT (score={thematic.get('score',0)})")
        if mob_status == "DOUBT":
            which.append(f"Mobility DOUBT")
        return {
            "decision": "DOUBT",
            "primary_reason": " + ".join(which),
            "reasons": reasons or which,
            "manual_review": True
        }
    
    if th_status == "INSUFFICIENT_EVIDENCE":
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "primary_reason": "Thematic: " + thematic.get("evidence",""),
            "reasons": ["Thematic INSUFFICIENT_EVIDENCE"],
            "manual_review": True
        }
    
    return {"decision": "PASS", "primary_reason": "All layers passed", "reasons": [], "manual_review": False}
