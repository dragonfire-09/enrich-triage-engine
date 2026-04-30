"""Green/Blue Transition thematic scoring."""
from typing import Dict, List


GREEN_TERMS = [
    "green transition", "renewable energy", "sustainability", "climate change",
    "circular economy", "decarbonization", "carbon neutral", "biodiversity",
    "clean energy", "net zero", "emissions reduction", "energy efficiency"
]

BLUE_TERMS = [
    "blue economy", "marine", "ocean", "maritime", "aquaculture",
    "coastal", "fisheries", "marine biodiversity", "sea", "blue transition"
]

INDIRECT_TERMS = [
    "environment", "ecological", "ecosystem", "pollution", "waste",
    "water quality", "air quality", "biodegradable", "green technology"
]


def score_thematic(proposal_text: str) -> Dict:
    """Return thematic relevance score + decision."""
    if not proposal_text.strip():
        return {
            "score": 0.0,
            "decision": "INSUFFICIENT_EVIDENCE",
            "green_hits": [],
            "blue_hits": [],
            "indirect_hits": [],
            "evidence": "Proposal text not extracted"
        }
    
    text_lower = proposal_text.lower()
    
    green_hits = [t for t in GREEN_TERMS if t in text_lower]
    blue_hits = [t for t in BLUE_TERMS if t in text_lower]
    indirect_hits = [t for t in INDIRECT_TERMS if t in text_lower]
    
    direct_score = min(1.0, (len(green_hits) + len(blue_hits)) * 0.15)
    indirect_score = min(0.4, len(indirect_hits) * 0.08)
    score = direct_score + indirect_score
    
    if score >= 0.6:
        decision = "PASS"
    elif score >= 0.3:
        decision = "DOUBT"
    elif indirect_hits:
        decision = "DOUBT"
    else:
        decision = "FAIL"
    
    return {
        "score": round(score, 2),
        "decision": decision,
        "green_hits": green_hits,
        "blue_hits": blue_hits,
        "indirect_hits": indirect_hits,
        "evidence": f"Direct: {len(green_hits)+len(blue_hits)} | Indirect: {len(indirect_hits)}"
    }
