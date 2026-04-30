"""Final decision aggregation with Turkish bucket names per system prompt.

FIX: aggregate_decision now accepts an optional `scientific` dict and
forces MANUAL_REVIEW when scientific quality is WEAK or weighted_total < 50.
Backward compatible: legacy 4-parameter calls still work unchanged.
"""
from typing import Dict, Optional


# System prompt buckets (Turkish)
BUCKET_PHD = "PHD_UYUMSUZ"
BUCKET_TEMATIK = "TEMATIK_UYUMSUZ"
BUCKET_FORMAL = "FORMAL_UYUMSUZ"
BUCKET_MOBILITE = "MOBILITE_UYUMSUZ"
BUCKET_MOBILITY_DOUBT = "MOBILITY_DOUBT"
BUCKET_PASS = "PASS"
BUCKET_MANUAL = "MANUAL_REVIEW"

# Scientific quality gate thresholds
WEAK_BANDS = {"WEAK", "VERY_WEAK", "POOR"}
SCIENTIFIC_MIN_TOTAL = 50.0


def aggregate_decision(
    phd: Dict,
    formal: Dict,
    thematic: Dict,
    mobility: Dict,
    scientific: Optional[Dict] = None,
) -> Dict:
    """Combine all layer decisions per system-prompt bucket priority.
    
    Priority order:
      1. PhD clearly fails → PHD_UYUMSUZ
      2. Thematic clearly fails → TEMATIK_UYUMSUZ
      3. Formal clearly fails → FORMAL_UYUMSUZ
      4. Mobility clearly fails → MOBILITE_UYUMSUZ
      5. Mobility uncertain → MOBILITY_DOUBT
      6. Evidence insufficient → MANUAL_REVIEW
      7. Scientific quality WEAK → MANUAL_REVIEW   (FIX)
      8. Else → PASS
    
    Parameters:
      scientific: optional dict {"band": str, "weighted_total_100": float}.
                  If None, the scientific gate is skipped (legacy behavior).
    """
    
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
    
    # 4. Mobility clearly fails
    mob_status = mobility.get("status", "PASS")
    if mob_status == "FAIL":
        return {
            "decision": BUCKET_MOBILITE,
            "primary_reason": f"Mobility FAIL: {mobility.get('turkey_months')} months in TR",
            "reasons": [mobility.get("evidence", "")],
            "manual_review": False
        }
    
    # 6. Evidence insufficient
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
    
    # 7. FIX: Scientific quality gate (only when scientific dict is provided)
    if scientific is not None:
        band = str(scientific.get("band", "") or "").strip().upper()
        try:
            total = float(scientific.get("weighted_total_100", 0) or 0)
        except (TypeError, ValueError):
            total = 0.0
        
        if band in WEAK_BANDS:
            return {
                "decision": BUCKET_MANUAL,
                "primary_reason": f"Scientific quality WEAK (band={band}, total={total:.1f}/100)",
                "reasons": [
                    f"Weighted total {total:.1f}/100 below acceptable threshold",
                    "Low excellence/impact/implementation scores require human evaluator review",
                ],
                "manual_review": True
            }
        if total > 0 and total < SCIENTIFIC_MIN_TOTAL:
            return {
                "decision": BUCKET_MANUAL,
                "primary_reason": f"Scientific quality below threshold (total={total:.1f} < {SCIENTIFIC_MIN_TOTAL})",
                "reasons": [f"Weighted total {total:.1f}/100 < {SCIENTIFIC_MIN_TOTAL}"],
                "manual_review": True
            }
    
    # 8. PASS
    return {
        "decision": BUCKET_PASS,
        "primary_reason": "All layers passed",
        "reasons": [],
        "manual_review": False
    }
