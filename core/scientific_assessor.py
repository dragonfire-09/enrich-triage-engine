"""Scientific quality assessment via LLM (OpenRouter).

Uses OpenAI SDK pointed to OpenRouter base URL.
Returns Excellence/Impact/Implementation scores (0-5),
strengths, weaknesses, verdict.
"""
import json
from typing import Dict, Optional


SYSTEM_PROMPT_SCIENTIFIC = """You are an ultra-rigorous scientific evaluator for an ENRICH-like postdoc fellowship.
You MUST output STRICTLY valid JSON only, no other text.

Evaluate the proposal on three axes (each 0-5 integer):

1. EXCELLENCE (0-5):
   - clarity and ambition of objectives
   - beyond state of the art
   - methodological soundness
   - interdisciplinarity if relevant
   - open science logic if relevant
   - applicant competence
   - supervisor fit
   - secondment fit if applicable

2. IMPACT (0-5):
   - career development and employability
   - dissemination / communication / exploitation logic
   - scientific / societal / economic relevance

3. IMPLEMENTATION (0-5):
   - work plan coherence
   - work packages / timeline / milestones if present
   - risks and mitigation

SCORING GUIDE:
- 5 = exceptional, top-tier
- 4 = strong, competitive
- 3 = ordinary, acceptable
- 2 = weak
- 1 = very weak
- 0 = not addressed at all

OUTPUT JSON SCHEMA:
{
  "excellence_score_5": <int 0-5>,
  "impact_score_5": <int 0-5>,
  "implementation_score_5": <int 0-5>,
  "excellence_rationale": "<1-2 sentences in Turkish>",
  "impact_rationale": "<1-2 sentences in Turkish>",
  "implementation_rationale": "<1-2 sentences in Turkish>",
  "major_strengths": ["<strength 1 in Turkish>", "<strength 2>", "<strength 3>"],
  "major_weaknesses": ["<weakness 1 in Turkish>", "<weakness 2>", "<weakness 3>"],
  "one_paragraph_verdict": "<3-5 sentence verdict in Turkish>",
  "evidence_gaps": "<what info was missing, in Turkish or 'NONE'>",
  "rule_ambiguity": "<any ambiguity, in Turkish or 'NONE'>"
}

If the proposal text is too short or empty, return all scores as 0 and set
evidence_gaps to "Proposal text empty or image-based".
"""


def _empty_assessment(reason: str) -> Dict:
    return {
        "excellence_score_5": 0,
        "impact_score_5": 0,
        "implementation_score_5": 0,
        "excellence_rationale": reason,
        "impact_rationale": reason,
        "implementation_rationale": reason,
        "major_strengths": ["INSUFFICIENT_EVIDENCE"],
        "major_weaknesses": ["INSUFFICIENT_EVIDENCE"],
        "one_paragraph_verdict": reason,
        "evidence_gaps": reason,
        "rule_ambiguity": "NONE",
        "weighted_total_100": 0.0,
        "scientific_quality_band": "VERY_WEAK",
        "llm_used": False,
        "llm_error": reason,
    }


def _band_from_total(total: float) -> str:
    if total >= 85:
        return "VERY_STRONG"
    elif total >= 70:
        return "STRONG"
    elif total >= 55:
        return "ORDINARY"
    elif total >= 35:
        return "WEAK"
    else:
        return "VERY_WEAK"


def assess_scientific_quality(
    proposal_text: str,
    cv_text: str = "",
    api_key: Optional[str] = None,
    model: str = "openai/gpt-4o-mini",
    base_url: str = "https://openrouter.ai/api/v1",
) -> Dict:
    """Run LLM-based scientific quality assessment.
    
    Returns dict with scores, rationales, strengths, weaknesses, verdict.
    Falls back gracefully on API errors.
    """
    if not api_key:
        return _empty_assessment("LLM disabled — no API key provided")
    
    if not proposal_text or len(proposal_text.strip()) < 200:
        return _empty_assessment("Proposal text too short or image-based")
    
    # Trim to fit context budget (~10K tokens of input safe for any model)
    proposal_clip = proposal_text[:15000]
    cv_clip = (cv_text or "")[:5000]
    
    user_prompt = f"""PROPOSAL TEXT:
---
{proposal_clip}
---

CV TEXT (for applicant competence assessment):
---
{cv_clip if cv_clip.strip() else "[CV section empty or image-based]"}
---

Evaluate per the rubric. Output ONLY the JSON object."""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SCIENTIFIC},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"} if "gpt" in model.lower() else None,
        )
        raw = response.choices[0].message.content.strip()
        
        # Some models wrap JSON in markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:].strip()
        
        data = json.loads(raw)
        
        # Compute weighted total (Excellence 50%, Impact 30%, Impl 20%)
        e = max(0, min(5, int(data.get("excellence_score_5", 0))))
        i = max(0, min(5, int(data.get("impact_score_5", 0))))
        im = max(0, min(5, int(data.get("implementation_score_5", 0))))
        
        weighted = (e * 0.5 + i * 0.3 + im * 0.2) * 20  # to 0-100
        
        data["excellence_score_5"] = e
        data["impact_score_5"] = i
        data["implementation_score_5"] = im
        data["weighted_total_100"] = round(weighted, 1)
        data["scientific_quality_band"] = _band_from_total(weighted)
        data["llm_used"] = True
        data["llm_model"] = model
        data["llm_error"] = None
        
        # Ensure list fields are lists
        for k in ("major_strengths", "major_weaknesses"):
            if isinstance(data.get(k), str):
                data[k] = [data[k]]
            if not data.get(k):
                data[k] = ["INSUFFICIENT_EVIDENCE"]
        
        return data
    
    except Exception as e:
        return _empty_assessment(f"LLM error: {str(e)[:200]}")
