"""Final decision aggregation with Turkish bucket names per system prompt."""
from typing import Dict


# System prompt buckets (Turkish)
BUCKET_PHD = "PHD_UYUMSUZ"
BUCKET_TEMATIK = "TEMATIK_UYUMSUZ"
BUCKET_FORMAL = "FORMAL_UYUMSUZ"
BUCKET_MOBILITE = "MOBILITE_UYUMSUZ"
BUCKET_MOBILITY_DOUBT = "MOBILITY_DOUBT"
BUCKET_PASS = "PASS"
BUCKET_MANUAL = "MANUAL_REVIEW"


def aggregate_decision(phd: Dict, formal: Dict, thematic: Dict, mobility: Dict) -> Dict:
    """Combine all layer decisions per system-prompt bucket priority.
    
    Priority order (per system prompt):
      1. PhD clearly fails → PHD_UYUMSUZ
      2. Thematic clearly fails → TEMATIK_UYUMSUZ
      3. Formal clearly fails → FORMAL_UYUMSUZ
      4. Mobility clearly fails → MOBILITE_UYUMSUZ
      5. Mobility uncertain → MOBILITY_DOUBT
      6. Evidence insufficient → MANUAL_REVIEW
      7. Else → PASS
    """
    reasons = []
    
    # 1. PhD checks
    if phd.get("found") is False:
        return {
            "decision": BUCKET_MANUAL,
            "primary_reason": "PhD date not extractable",
            "reasons": ["PhD date not found"],
            "manual_review": True
        }
    if phd.get("eligible") is False:
        return {
            "decision": BUCKET_PHD,
            "primary_reason": f"PhD/defense date {phd.get('date')} > deadline (30 Apr 2026)",
            "reasons": [phd.get("evidence_quote", "")],
            "manual_review": False
        }
    
    # 2. Thematic clearly fails
    if thematic.get("decision") == "FAIL":
        return {
            "decision": BUCKET_TEMATIK,
            "primary_reason": f"Thematic FAIL (score={thematic.get('score', 0)})",
            "reasons": [thematic.get("evidence", "")],
            "manual_review": True
        }
    
    # 3. Formal clearly fails
    if formal.get("decision") == "FAIL":
        return {
            "decision": BUCKET_FORMAL,
            "primary_reason": "Formal: " + "; ".join(formal.get("issues", [])),
            "reasons": formal.get("issues", []),
            "manual_review": False
        }
    
    # 4-5. Mobility checks
    mob_status = mobility.get("status", "PASS")
    if mob_status == "FAIL":
        return {
            "decision": BUCKET_MOBILITE,
            "primary_reason": f"Mobility FAIL: {mobility.get('turkey_months')} months in TR",
            "reasons": [mobility.get("evidence", "")],
            "manual_review": False
        }
    
    # 6. Evidence insufficient (any layer)
    if mob_status == "INSUFFICIENT_EVIDENCE":
        return {
            "decision": BUCKET_MANUAL,
            "primary_reason": f"Mobility INSUFFICIENT_EVIDENCE: {mobility.get('evidence', '')}",
            "reasons": ["CV may be image-based; OCR or manual review needed"],
            "manual_review": True
        }
    
    if thematic.get("decision") == "INSUFFICIENT_EVIDENCE":
        return {
            "decision": BUCKET_MANUAL,
            "primary_reason": f"Thematic INSUFFICIENT_EVIDENCE: {thematic.get('evidence','')}",
            "reasons": ["Proposal may be image-based"],
            "manual_review": True
        }
    
    # 5. Mobility doubt
    if mob_status == "DOUBT":
        return {
            "decision": BUCKET_MOBILITY_DOUBT,
            "primary_reason": f"Mobility DOUBT: {mobility.get('evidence', '')}",
            "reasons": [mobility.get("evidence", "")],
            "manual_review": True
        }
    
    # Thematic doubt → manual review
    if thematic.get("decision") == "DOUBT":
        return {
            "decision": BUCKET_MANUAL,
            "primary_reason": f"Thematic DOUBT (score={thematic.get('score', 0)})",
            "reasons": [thematic.get("evidence", "")],
            "manual_review": True
        }
    
    # 7. PASS
    return {
        "decision": BUCKET_PASS,
        "primary_reason": "All layers passed",
        "reasons": [],
        "manual_review": False
    }
