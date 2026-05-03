"""Green/Blue Transition thematic scoring — Horizon Europe & EU Green Deal aligned.

Coverage:
- EU Green Deal core terminology
- Horizon Europe Mission Areas (Climate Adaptation, Ocean, Cities, Soil)
- EU Battery Alliance + Hydrogen Strategy
- Critical Raw Materials Act
- Blue Economy + Mission Ocean
- Industrial Decarbonization (Steel, CCUS, Cement)
- Sustainable Agriculture + Soil Health
- Indirect enablers (governance, equity, health)

Scoring:
- Direct hits (Green/Blue): up to 1.0 contribution (15% per term, cap 1.0)
- Indirect hits: up to 0.4 contribution (6% per term, cap 0.4)
- Combined score clamped to [0.0, 1.0] → multiplied by 100 for display

Confidence (system prompt aligned):
- Computed from total_hits density
- Decision uses BOTH score AND confidence per system prompt rule:
    score < pass_threshold       → FAIL
    score >= pass AND conf < 0.7 → DOUBT
    score >= pass AND conf >= 0.7 → PASS

FIXES:
- Word-boundary regex (no substring false positives)
- Score capped at [0.0, 1.0]
- Confidence-based DOUBT logic per system prompt
"""
import re
from typing import Dict, List, Tuple, Pattern


# =========================================================================
# GREEN TRANSITION TERMS — EU Green Deal + Horizon Europe Missions
# =========================================================================
GREEN_TERMS = [
    # --- Core climate & sustainability ---
    "green transition", "green deal", "european green deal",
    "renewable energy", "renewables", "sustainability", "sustainable",
    "climate change", "climate action", "climate adaptation",
    "climate mitigation", "climate resilience", "climate-neutral",
    "climate neutrality", "climate emergency", "climate crisis",
    "circular economy", "circularity", "circular bioeconomy",
    "decarbonization", "decarbonisation", "carbon neutral",
    "carbon neutrality", "net zero", "net-zero", "zero emissions",
    "emissions reduction", "ghg reduction", "greenhouse gas",
    "energy efficiency", "energy poverty", "just transition",
    "biodiversity", "ecosystem services", "nature-based solutions",
    "nature based solutions", "rewilding", "natural capital",
    
    # --- Renewable energy specifics ---
    "wind energy", "wind turbine", "wind farm", "offshore wind",
    "onshore wind", "solar energy", "solar power", "solar cell",
    "photovoltaic", "photovoltaics", "pv panel", "concentrated solar",
    "hydroelectric", "hydropower", "geothermal", "bioenergy",
    "biomass", "biofuel", "biogas", "biomethane",
    "tidal energy", "wave energy", "marine renewable",
    "ocean energy", "renewable hydrogen", "green hydrogen",
    
    # --- Energy storage & batteries (EU Battery Alliance) ---
    "battery", "batteries", "battery storage", "energy storage",
    "solid-state battery", "solid state battery", "all-solid",
    "lithium-ion", "lithium ion", "li-ion", "sodium-ion", "na-ion",
    "fluoride-ion", "fluoride ion", "redox flow", "flow battery",
    "cathode", "anode", "electrolyte", "supercapacitor",
    "fuel cell", "fuel cells", "hydrogen storage", "hydrogen economy",
    "thermal storage", "grid storage", "stationary storage",
    "battery recycling", "second-life battery",
    
    # --- Electromobility ---
    "electric vehicle", "electric vehicles", "electromobility",
    "e-mobility", "emobility", "charging infrastructure",
    "electric mobility", "zero-emission vehicle",
    "sustainable transport", "sustainable mobility", "clean mobility",
    "low-emission transport", "alternative fuels",
    
    # --- Smart grid & energy systems ---
    "smart grid", "smart energy", "energy management",
    "demand response", "energy community", "energy citizen",
    "microgrid", "distributed energy", "power grid modernization",
    "energy flexibility", "energy transition",
    
    # --- Critical raw materials & strategic autonomy ---
    "critical raw materials", "critical raw material",
    "strategic autonomy", "strategic raw materials",
    "non-critical element", "non-critical elements",
    "abundant element", "abundant elements", "earth-abundant",
    "raw material", "resource efficiency", "material efficiency",
    "secondary raw materials", "urban mining",
    
    # --- Industrial decarbonization ---
    "low-carbon", "low carbon", "low-emission",
    "green steel", "green cement", "green chemistry",
    "carbon capture", "ccs", "ccus", "carbon storage",
    "carbon utilization", "carbon dioxide removal",
    "direct air capture", "industrial symbiosis",
    "clean industry", "green manufacturing",
    
    # --- Mission: Adaptation to Climate Change ---
    "adaptation strategy", "climate risk",
    "disaster risk reduction", "drought management",
    "flood management", "heatwave", "extreme weather",
    "climate vulnerability", "early warning system",
    "resilient infrastructure", "climate-proof",
    
    # --- Mission: Climate-Neutral and Smart Cities ---
    "climate-neutral cities", "smart city", "smart cities",
    "urban transition", "sustainable city", "green city",
    "urban green", "green building", "green construction",
    "passive house", "near-zero energy building", "nzeb",
    "renovation wave", "urban planning", "sustainable urban mobility",
    "15-minute city",
    
    # --- Mission: A Soil Deal for Europe ---
    "soil health", "healthy soil", "soil deal",
    "soil restoration", "land degradation", "desertification",
    "regenerative agriculture", "agroecology", "agroforestry",
    "sustainable agriculture", "sustainable food system",
    "farm to fork", "organic farming", "pesticide reduction",
    "nutrient management", "carbon farming", "soil carbon",
    
    # --- Pollution & waste ---
    "pollution prevention", "zero pollution", "air pollution",
    "water pollution", "soil pollution", "plastic pollution",
    "microplastic", "waste reduction", "waste management",
    "zero waste", "recycling", "upcycling", "biodegradable",
    "compostable", "single-use plastic",
    
    # --- Generic green tech ---
    "green technology", "cleantech", "clean technology",
    "eco-innovation", "ecoinnovation", "eco-design", "ecodesign",
    "environmental innovation", "sustainable innovation",
]


# =========================================================================
# BLUE TRANSITION TERMS — Mission Ocean + Blue Economy
# =========================================================================
BLUE_TERMS = [
    "blue economy", "blue transition", "blue growth",
    "sustainable blue economy", "blue deal", "blue carbon",
    
    "marine", "marine ecosystem", "marine biodiversity",
    "marine environment", "marine habitat", "marine pollution",
    "marine conservation", "marine spatial planning",
    "marine protected area", "marine litter",
    "marine renewable", "marine biotechnology",
    
    "ocean", "ocean health", "ocean acidification",
    "ocean conservation", "ocean governance", "ocean literacy",
    "ocean energy", "ocean observation", "deep sea", "deep-sea",
    "high seas", "open ocean", "ocean current",
    "restore our ocean", "mission ocean",
    
    "coastal", "coastal zone", "coastal resilience",
    "coastal erosion", "coastal management", "coastal community",
    "maritime", "maritime sector", "maritime industry",
    "shipping", "sustainable shipping", "green shipping",
    "port", "green port", "sustainable port",
    
    "fisheries", "fishery", "sustainable fisheries",
    "small-scale fisheries", "aquaculture", "sustainable aquaculture",
    "fish stock", "overfishing", "by-catch", "iuu fishing",
    "seafood", "sustainable seafood", "blue food",
    
    "sea", "sea level", "sea level rise", "freshwater",
    "water resources", "water quality", "water management",
    "water scarcity", "drought", "wastewater", "wastewater treatment",
    "river basin", "watershed", "estuary", "wetland",
    "water-energy nexus",
    
    "marine debris", "ghost net",
    "plastic in ocean", "ocean plastic", "marine plastic",
    
    "marine energy", "offshore renewable", "floating wind",
]


# =========================================================================
# INDIRECT TERMS — Cross-cutting enablers
# =========================================================================
INDIRECT_TERMS = [
    "environment", "environmental", "ecological", "ecology",
    "ecosystem", "habitat", "biosphere",
    
    "pollution", "pollutant", "contamination", "waste",
    "biodegradable", "non-toxic", "ecotoxicology",
    
    "governance", "policy", "regulation", "framework",
    "stakeholder", "participatory", "co-creation", "co-design",
    "public engagement", "citizen science", "civil society",
    "social science", "political economy", "political ecology",
    
    "interdisciplinary", "transdisciplinary", "multidisciplinary",
    "transition", "transformation", "systemic change",
    "paradigm shift", "innovation system",
    
    "global south", "developing countries", "developing country",
    "least developed countries", "low-income country",
    "equity", "equality", "justice", "environmental justice",
    "climate justice", "energy justice", "social justice",
    "intersectionality", "marginalized", "vulnerable communities",
    "indigenous", "indigenous knowledge", "traditional knowledge",
    
    "health", "human health", "planetary health",
    "wellbeing", "well-being", "public health", "one health",
    "environmental health", "occupational health",
    
    "community", "local community", "rural community",
    "urban community", "society", "social impact",
    "social innovation", "behavior change", "behavioural change",
    
    "green finance", "sustainable finance", "esg",
    "green bond", "green investment", "impact investment",
    "sustainable development", "sdg", "sustainable development goals",
    
    "education", "training", "capacity building", "literacy",
    "awareness", "skills development", "lifelong learning",
    
    "digital twin", "digitalization", "digital transition",
    "twin transition", "ai for sustainability",
    "data-driven", "open data", "open science",
    
    "bio-based", "biobased", "bioeconomy", "bio-economy",
    "biotechnology", "synthetic biology",
]


# =========================================================================
# WORD-BOUNDARY PATTERN COMPILATION
# =========================================================================
def _compile_patterns(terms: List[str]) -> List[Tuple[str, Pattern]]:
    """Pre-compile each term as a word-boundary regex."""
    return [(t, re.compile(r"\b" + re.escape(t) + r"\b")) for t in terms]


_GREEN_PATTERNS = _compile_patterns(GREEN_TERMS)
_BLUE_PATTERNS = _compile_patterns(BLUE_TERMS)
_INDIRECT_PATTERNS = _compile_patterns(INDIRECT_TERMS)


# =========================================================================
# CONFIDENCE COMPUTATION (NEW — system prompt aligned)
# =========================================================================
def _compute_confidence(direct_count: int, indirect_count: int, score: float) -> float:
    """Confidence reflects how reliably we can claim Green/Blue alignment.
    
    System prompt says:
      - score >= pass AND confidence < 0.7 → DOUBT
      - score >= pass AND confidence >= 0.7 → PASS
    
    Heuristic:
      - Direct hits weigh more than indirect (they are anchor terms)
      - 5+ direct hits → very high confidence (0.95)
      - 3+ direct hits → high confidence (0.80)
      - 2 direct hits + indirect support → medium-high (0.70)
      - 1 direct hit + indirect support → medium (0.55)
      - Indirect-only → low (0.30)
      - Nothing → 0.0
    """
    if direct_count >= 5:
        conf = 0.95
    elif direct_count >= 3:
        conf = 0.80
    elif direct_count == 2:
        conf = 0.70 if indirect_count >= 2 else 0.60
    elif direct_count == 1:
        conf = 0.55 if indirect_count >= 3 else 0.45
    elif indirect_count >= 3:
        conf = 0.30
    elif indirect_count >= 1:
        conf = 0.20
    else:
        conf = 0.0
    
    return round(conf, 2)


# =========================================================================
# MAIN SCORING FUNCTION
# =========================================================================
def score_thematic(
    proposal_text: str,
    pass_threshold: float = 0.6,
    doubt_threshold: float = 0.3,  # legacy, kept for backward compat
    confidence_threshold: float = 0.7,  # NEW: system prompt aligned
    min_text_length: int = 300,
) -> Dict:
    """Return thematic relevance score + decision.
    
    Decision logic (system prompt aligned):
      score < pass_threshold       → FAIL
      score >= pass AND conf < 0.7 → DOUBT
      score >= pass AND conf >= 0.7 → PASS
    
    FIX history:
      - Score capped at [0.0, 1.0]
      - Word-boundary regex (no substring FP)
      - Confidence-based DOUBT (NEW, system prompt aligned)
    """
    text = (proposal_text or "").strip()
    
    if len(text) < min_text_length:
        return {
            "score": 0.0,
            "confidence": 0.0,
            "decision": "INSUFFICIENT_EVIDENCE",
            "green_hits": [],
            "blue_hits": [],
            "indirect_hits": [],
            "evidence": f"Proposal text too short ({len(text)} chars) — possibly image-based, OCR may be required",
            "thresholds_used": {
                "pass": pass_threshold,
                "doubt": doubt_threshold,
                "confidence": confidence_threshold,
            }
        }
    
    text_lower = text.lower()
    
    green_hits = sorted({t for t, pat in _GREEN_PATTERNS if pat.search(text_lower)})
    blue_hits = sorted({t for t, pat in _BLUE_PATTERNS if pat.search(text_lower)})
    indirect_hits = sorted({t for t, pat in _INDIRECT_PATTERNS if pat.search(text_lower)})
    
    direct_count = len(green_hits) + len(blue_hits)
    indirect_count = len(indirect_hits)
    
    direct_score = min(1.0, direct_count * 0.15)
    indirect_score = min(0.4, indirect_count * 0.06)
    score = round(min(1.0, direct_score + indirect_score), 2)
    
    # NEW: compute confidence per system prompt
    confidence = _compute_confidence(direct_count, indirect_count, score)
    
    total_hits = direct_count + indirect_count
    
    # NEW: decision logic per system prompt
    if score < pass_threshold:
        # Below pass: still allow DOUBT for weak signals (Codex #6)
        if score >= doubt_threshold:
            decision = "DOUBT"
        elif total_hits >= 1:
            decision = "DOUBT"
        else:
            decision = "FAIL"
    else:
        # At or above pass: confidence determines PASS vs DOUBT (system prompt rule)
        if confidence >= confidence_threshold:
            decision = "PASS"
        else:
            decision = "DOUBT"
    
    return {
        "score": score,
        "confidence": confidence,
        "decision": decision,
        "green_hits": green_hits,
        "blue_hits": blue_hits,
        "indirect_hits": indirect_hits,
        "evidence": (
            f"Direct: {direct_count} | Indirect: {indirect_count} | "
            f"Score: {score} | Confidence: {confidence}"
        ),
        "thresholds_used": {
            "pass": pass_threshold,
            "doubt": doubt_threshold,
            "confidence": confidence_threshold,
        }
    }
