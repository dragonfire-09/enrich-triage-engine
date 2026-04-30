"""Green/Blue Transition thematic scoring.

v2 (Codex #6 fix):
  - FAIL only when text is meaningful AND zero anchors
  - Weak signals → DOUBT (manual review), not auto-FAIL
  - Image-based proposals → INSUFFICIENT_EVIDENCE
"""
from typing import Dict, List


GREEN_TERMS = [
    "green transition", "renewable energy", "sustainability", "climate change",
    "circular economy", "decarbonization", "carbon neutral", "biodiversity",
    "clean energy", "net zero", "emissions reduction", "energy efficiency",
    "sustainable", "renewable", "climate", "carbon", "green technology",
]

BLUE_TERMS = [
    "blue economy", "marine", "ocean", "maritime", "aquaculture",
    "coastal", "fisheries", "marine biodiversity", "sea", "blue transition",
    "water resources", "freshwater",
]

INDIRECT_TERMS = [
    "environment", "ecological", "ecosystem", "pollution", "waste",
    "water quality", "air quality", "biodegradable",
    "governance", "policy", "social science", "stakeholder",
    "interdisciplinary", "transition", "transformation",
    "global south", "developing countries", "equity", "justice",
    "health", "wellbeing", "public", "community",
]


def score_thematic(proposal_text: str) -> Dict:
    """Return thematic relevance score + decision.
    
    Decision logic:
      - text empty / image-based → INSUFFICIENT_EVIDENCE
      - score >= 0.6 → PASS
      - score >= 0.3 → DOUBT
      - 0 < score < 0.3 → DOUBT (Codex #6: weak signals → manual review)
      - score == 0 AND text is meaningful → FAIL (truly off-topic)
      - score == 0 AND text is sparse → INSUFFICIENT_EVIDENCE
    """
    text = (proposal_text or "").strip()
    
    # Image-based / empty proposal
    if len(text) < 300:
        return {
            "score": 0.0,
            "decision": "INSUFFICIENT_EVIDENCE",
            "green_hits": [],
            "blue_hits": [],
            "indirect_hits": [],
            "evidence": "Proposal text too short — possibly image-based, OCR may be required"
        }
    
    text_lower = text.lower()
    
    green_hits = [t for t in GREEN_TERMS if t in text_lower]
    blue_hits = [t for t in BLUE_TERMS if t in text_lower]
    indirect_hits = [t for t in INDIRECT_TERMS if t in text_lower]
    
    direct_count = len(green_hits) + len(blue_hits)
    indirect_count = len(indirect_hits)
    
    direct_score = min(1.0, direct_count * 0.15)
    indirect_score = min(0.4, indirect_count * 0.06)
    score = round(direct_score + indirect_score, 2)
    
    total_hits = direct_count + indirect_count
    
    # Decision logic per Codex #6
    if score >= 0.6:
        decision = "PASS"
    elif score >= 0.3:
        decision = "DOUBT"
    elif total_hits >= 1:
        # Some signal exists but weak → DOUBT, not FAIL
        decision = "DOUBT"
    else:
        # Truly zero anchors in a meaningful text → FAIL
        decision = "FAIL"
    
    return {
        "score": score,
        "decision": decision,
        "green_hits": green_hits,
        "blue_hits": blue_hits,
        "indirect_hits": indirect_hits,
        "evidence": f"Direct: {direct_count} | Indirect: {indirect_count}"
    }
