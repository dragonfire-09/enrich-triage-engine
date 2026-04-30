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
"""
from typing import Dict, List


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
    "critical raw materials", "crm", "critical raw material",
    "strategic autonomy", "strategic raw materials",
    "non-critical element", "non-critical elements",
    "abundant element", "abundant elements", "earth-abundant",
    "raw material", "resource efficiency", "material efficiency",
    "secondary raw materials", "urban mining",
    
    # --- Industrial decarbonization ---
    "low-carbon", "low carbon", "low-emission",
    "green steel", "green cement", "green chemistry",
    "carbon capture", "ccs", "ccus", "carbon storage",
    "carbon utilization", "carbon dioxide removal", "cdr",
    "direct air capture", "dac", "industrial symbiosis",
    "clean industry", "green manufacturing",
    
    # --- Mission: Adaptation to Climate Change ---
    "climate adaptation", "adaptation strategy", "climate risk",
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
    "sump", "15-minute city",
    
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
    # --- Core blue economy ---
    "blue economy", "blue transition", "blue growth",
    "sustainable blue economy", "blue deal", "blue carbon",
    
    # --- Marine ecosystems ---
    "marine", "marine ecosystem", "marine biodiversity",
    "marine environment", "marine habitat", "marine pollution",
    "marine conservation", "marine spatial planning", "msp",
    "marine protected area", "mpa", "marine litter",
    "marine renewable", "marine biotechnology",
    
    # --- Ocean ---
    "ocean", "ocean health", "ocean acidification",
    "ocean conservation", "ocean governance", "ocean literacy",
    "ocean energy", "ocean observation", "deep sea", "deep-sea",
    "high seas", "open ocean", "ocean current",
    "restore our ocean", "mission ocean",
    
    # --- Coastal & maritime ---
    "coastal", "coastal zone", "coastal resilience",
    "coastal erosion", "coastal management", "coastal community",
    "maritime", "maritime sector", "maritime industry",
    "shipping", "sustainable shipping", "green shipping",
    "port", "green port", "sustainable port",
    
    # --- Fisheries & aquaculture ---
    "fisheries", "fishery", "sustainable fisheries",
    "small-scale fisheries", "aquaculture", "sustainable aquaculture",
    "fish stock", "overfishing", "by-catch", "iuu fishing",
    "seafood", "sustainable seafood", "blue food",
    
    # --- Water resources ---
    "sea", "sea level", "sea level rise", "freshwater",
    "water resources", "water quality", "water management",
    "water scarcity", "drought", "wastewater", "wastewater treatment",
    "river basin", "watershed", "estuary", "wetland",
    "water-energy nexus",
    
    # --- Marine pollution / litter ---
    "marine pollution", "marine debris", "ghost net",
    "plastic in ocean", "ocean plastic", "marine plastic",
    
    # --- Marine renewable energy ---
    "tidal energy", "wave energy", "marine energy",
    "offshore renewable", "offshore wind", "floating wind",
]


# =========================================================================
# INDIRECT TERMS — Cross-cutting enablers (governance, equity, health, etc.)
# =========================================================================
INDIRECT_TERMS = [
    # --- Environment general ---
    "environment", "environmental", "ecological", "ecology",
    "ecosystem", "habitat", "biosphere",
    
    # --- Pollution / quality ---
    "pollution", "pollutant", "contamination", "waste",
    "water quality", "air quality", "soil quality",
    "biodegradable", "non-toxic", "ecotoxicology",
    
    # --- Governance & policy ---
    "governance", "policy", "regulation", "framework",
    "stakeholder", "participatory", "co-creation", "co-design",
    "public engagement", "citizen science", "civil society",
    "social science", "political economy", "political ecology",
    
    # --- Cross-cutting research ---
    "interdisciplinary", "transdisciplinary", "multidisciplinary",
    "transition", "transformation", "systemic change",
    "paradigm shift", "innovation system",
    
    # --- Equity & justice ---
    "global south", "developing countries", "developing country",
    "least developed countries", "ldc", "low-income country",
    "equity", "equality", "justice", "environmental justice",
    "climate justice", "energy justice", "social justice",
    "intersectionality", "marginalized", "vulnerable communities",
    "indigenous", "indigenous knowledge", "traditional knowledge",
    
    # --- Health & wellbeing ---
    "health", "human health", "planetary health",
    "wellbeing", "well-being", "public health", "one health",
    "environmental health", "occupational health",
    
    # --- Community & social ---
    "community", "local community", "rural community",
    "urban community", "society", "social impact",
    "social innovation", "behavior change", "behavioural change",
    
    # --- Economic & finance ---
    "green finance", "sustainable finance", "esg",
    "green bond", "green investment", "impact investment",
    "sustainable development", "sdg", "sustainable development goals",
    
    # --- Education & capacity ---
    "education", "training", "capacity building", "literacy",
    "awareness", "skills development", "lifelong learning",
    
    # --- Digital enablers ---
    "digital twin", "digitalization", "digital transition",
    "twin transition", "ai for sustainability",
    "data-driven", "open data", "open science",
    
    # --- Bio-based ---
    "bio-based", "biobased", "bioeconomy", "bio-economy",
    "biotechnology", "synthetic biology",
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
    
    FIX: combined score clamped to [0.0, 1.0] so *100 conversion never exceeds 100.
    Coverage expanded to Horizon Europe Mission Areas (Aug 2025).
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
    
    # Use word-boundary-ish matching: term in text_lower
    # (Multi-word terms naturally word-bounded; single words may catch substrings
    # but lists are curated to avoid false positives like "carbonate" matching "carbon")
    green_hits = sorted(set(t for t in GREEN_TERMS if t in text_lower))
    blue_hits = sorted(set(t for t in BLUE_TERMS if t in text_lower))
    indirect_hits = sorted(set(t for t in INDIRECT_TERMS if t in text_lower))
    
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
