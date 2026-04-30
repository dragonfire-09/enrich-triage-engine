"""Green/Blue Transition thematic scoring (parameterized)."""
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


def score_thematic(
    proposal_text: str,
    pass_threshold: float = 0.6,
    doubt_threshold: float = 0.3,
    min_text_length: int = 300,
) -> Dict:
    """Return thematic relevance score + decision.
    
    Parameters:
      pass_threshold:  score >= this → PASS
      doubt_threshold: score >= this AND < pass_threshold → DOUBT
      min_text_length: under this many chars → INSUFFICIENT_EVIDENCE
    
    Codex #6 fix: weak signals → DOUBT (not auto-FAIL).
    Hard FAIL only when text is meaningful AND ZERO anchors found.
    
    FIX: combined score is now clamped to [0.0, 1.0] so the *100 conversion
    in the export layer can never exceed 100.
    """
    text = (proposal_text or "").strip()
    
    if len(text) < min_text_length:
        return {
            "score": 0.0,
            "decision": "INSUFFICIENT_EVIDENCE",
            "green_hits": [],
            "blue_hits": [],
            "indirect_hits": [],
            "evidence": f"Proposal text too short ({len(text)} chars) — possibly image-based, OCR may be required",
            "thresholds_used": {"pass": pass_threshold, "doubt": doubt_threshold}
        }
    
    text_lower = text.lower()
    
    green_hits = [t for t in GREEN_TERMS if t in text_lower]
    blue_hits = [t for t in BLUE_TERMS if t in text_lower]
    indirect_hits = [t for t in INDIRECT_TERMS if t in text_lower]
    
    direct_count = len(green_hits) + len(blue_hits)
    indirect_count = len(indirect_hits)
    
    direct_score = min(1.0, direct_count * 0.15)
    indirect_score = min(0.4, indirect_count * 0.06)
    
    # FIX: clamp combined score to [0.0, 1.0]
    score = round(min(1.0, direct_score + indirect_score), 2)
    
    total_hits = direct_count + indirect_count
    
    if score >= pass_threshold:
        decision = "PASS"
    elif score >= doubt_threshold:
        decision = "DOUBT"
    elif total_hits >= 1:
        decision = "DOUBT"
    else:
        decision = "FAIL"
    
    return {
        "score": score,
        "decision": decision,
        "green_hits": green_hits,
        "blue_hits": blue_hits,
        "indirect_hits": indirect_hits,
        "evidence": f"Direct: {direct_count} | Indirect: {indirect_count}",
        "thresholds_used": {"pass": pass_threshold, "doubt": doubt_threshold}
    }
