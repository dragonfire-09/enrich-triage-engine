"""Excel + TSV export — 39 columns matching system prompt schema."""
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict


# Columns in EXACT order per system prompt
COLUMNS = [
    "file_name",
    "application_id",
    "applicant_name",
    "project_title",
    "nationality",
    "current_institution",
    "phd_date_raw",
    "phd_date_normalized",
    "phd_decision",
    "phd_evidence",
    "thematic_score_100",
    "thematic_confidence_100",
    "thematic_decision",
    "thematic_rationale_short",
    "proposal_page_count",
    "cv_page_count",
    "ethics_tables_present",
    "english_signal",
    "font_signal",
    "formatting_check",
    "template_contamination",
    "formal_decision",
    "formal_rationale_short",
    "mobility_window_start",
    "mobility_window_end",
    "turkiye_months_estimate",
    "mobility_decision",
    "mobility_confidence_100",
    "mobility_rationale_short",
    "excellence_score_5",
    "impact_score_5",
    "implementation_score_5",
    "weighted_total_100",
    "scientific_quality_band",
    "major_strengths",
    "major_weaknesses",
    "recommended_final_bucket",
    "manual_review_needed",
    "confidence_overall_100",
]


def _val(d, *keys, default="INSUFFICIENT_EVIDENCE"):
    """Safe nested get."""
    cur = d
    for k in keys:
        if cur is None:
            return default
        cur = cur.get(k) if isinstance(cur, dict) else None
    if cur is None or cur == "":
        return default
    return cur


def _semicolon_join(items):
    if not items:
        return "INSUFFICIENT_EVIDENCE"
    if isinstance(items, str):
        return items
    return "; ".join(str(x) for x in items[:5])


def _phd_decision_label(phd: Dict) -> str:
    if phd.get("found") is False:
        return "INSUFFICIENT_EVIDENCE"
    if phd.get("eligible") is False:
        return "PHD_INELIGIBLE"
    if phd.get("eligible") is True:
        return "PHD_ELIGIBLE"
    return "INSUFFICIENT_EVIDENCE"


def _thematic_decision_label(thematic: Dict) -> str:
    d = thematic.get("decision", "")
    return {
        "PASS": "THEMATIC_PASS",
        "DOUBT": "THEMATIC_DOUBT",
        "FAIL": "THEMATIC_FAIL",
        "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
    }.get(d, "INSUFFICIENT_EVIDENCE")


def _mobility_decision_label(mobility: Dict) -> str:
    s = mobility.get("status", "")
    return {
        "PASS": "MOBILITY_PASS",
        "FAIL": "MOBILITY_FAIL",
        "DOUBT": "MOBILITY_DOUBT",
        "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
    }.get(s, "INSUFFICIENT_EVIDENCE")


def _thematic_confidence(thematic: Dict) -> int:
    """Derive 0-100 confidence.
    
    FIX: Prefer the new `confidence` field from thematic_scorer.py
    (system-prompt-aligned). Fall back to legacy heuristic if absent
    (backward compatibility for older runs / cached results).
    """
    if thematic.get("decision") == "INSUFFICIENT_EVIDENCE":
        return 0
    
    # NEW: use confidence from thematic_scorer if available (0.0-1.0 → 0-100)
    if "confidence" in thematic and thematic["confidence"] is not None:
        try:
            return int(round(float(thematic["confidence"]) * 100))
        except (TypeError, ValueError):
            pass  # fall through to legacy heuristic
    
    # LEGACY fallback: hit-count heuristic
    hits = len(thematic.get("green_hits", [])) + len(thematic.get("blue_hits", []))
    indirect = len(thematic.get("indirect_hits", []))
    base = min(70, hits * 15 + indirect * 5)
    return min(100, base + 20 if hits >= 2 else base)


def _mobility_confidence(mobility: Dict) -> int:
    conf = mobility.get("confidence", "low")
    if mobility.get("status") == "INSUFFICIENT_EVIDENCE":
        return 0
    return {"high": 90, "medium": 65, "low": 35, "none": 0}.get(conf, 30)


def _overall_confidence(phd, formal, thematic, mobility, scientific) -> int:
    """Weighted overall confidence."""
    parts = []
    if phd.get("found"):
        parts.append({"high": 95, "medium": 70, "low": 40}.get(phd.get("confidence", "low"), 30))
    else:
        parts.append(20)
    parts.append(80 if formal.get("decision") == "PASS" else 50)
    parts.append(_thematic_confidence(thematic))
    parts.append(_mobility_confidence(mobility))
    if scientific and scientific.get("llm_used"):
        parts.append(75)
    else:
        parts.append(40)
    return int(sum(parts) / len(parts))


def results_to_dataframe(results: List[Dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        meta = r.get("metadata", {})
        phd = r.get("phd", {})
        formal = r.get("formal", {})
        thematic = r.get("thematic", {})
        mobility = r.get("mobility", {})
        scientific = r.get("scientific", {})
        final = r.get("final", {})
        
        # Thematic 0-100 score
        th_score_100 = round(thematic.get("score", 0) * 100) if thematic.get("score") is not None else 0
        th_conf = _thematic_confidence(thematic)
        mob_conf = _mobility_confidence(mobility)
        
        # Mobility window
        mob_window_start = "2023-04-30"
        mob_window_end = "2026-04-30"
        
        rows.append({
            "file_name": r.get("filename", "INSUFFICIENT_EVIDENCE"),
            "application_id": _val(meta, "application_id"),
            "applicant_name": _val(meta, "applicant_name"),
            "project_title": _val(meta, "project_title"),
            "nationality": _val(meta, "nationality"),
            "current_institution": _val(meta, "current_institution"),
            "phd_date_raw": (phd.get("evidence_quote") or "INSUFFICIENT_EVIDENCE")[:200],
            "phd_date_normalized": phd["date"].strftime("%Y-%m-%d") if phd.get("date") else "INSUFFICIENT_EVIDENCE",
            "phd_decision": _phd_decision_label(phd),
            "phd_evidence": (phd.get("evidence_quote") or "INSUFFICIENT_EVIDENCE")[:200],
            "thematic_score_100": th_score_100,
            "thematic_confidence_100": th_conf,
            "thematic_decision": _thematic_decision_label(thematic),
            "thematic_rationale_short": _semicolon_join(
                (thematic.get("green_hits", []) + thematic.get("blue_hits", []))[:5]
            ) if (thematic.get("green_hits") or thematic.get("blue_hits")) else thematic.get("evidence", "INSUFFICIENT_EVIDENCE"),
            "proposal_page_count": formal.get("proposal_pages", 0),
            "cv_page_count": formal.get("cv_pages", 0),
            "ethics_tables_present": _val(meta, "ethics_tables_present"),
            "english_signal": _val(meta, "english_signal"),
            "font_signal": "INSUFFICIENT_EVIDENCE",
            "formatting_check": "INSUFFICIENT_EVIDENCE",
            "template_contamination": "YES" if any("Template" in w for w in formal.get("warnings", [])) else "NO",
            "formal_decision": "FORMAL_PASS" if formal.get("decision") == "PASS" else (
                "FORMAL_FAIL" if formal.get("decision") == "FAIL" else "FORMAL_DOUBT"
            ),
            "formal_rationale_short": _semicolon_join(formal.get("warnings", []) + formal.get("issues", [])) or "All formal checks passed",
            "mobility_window_start": mob_window_start,
            "mobility_window_end": mob_window_end,
            "turkiye_months_estimate": mobility.get("turkey_months") if mobility.get("turkey_months") is not None else "INSUFFICIENT_EVIDENCE",
            "mobility_decision": _mobility_decision_label(mobility),
            "mobility_confidence_100": mob_conf,
            "mobility_rationale_short": (mobility.get("evidence") or "INSUFFICIENT_EVIDENCE")[:200],
            "excellence_score_5": scientific.get("excellence_score_5", 0) if scientific else 0,
            "impact_score_5": scientific.get("impact_score_5", 0) if scientific else 0,
            "implementation_score_5": scientific.get("implementation_score_5", 0) if scientific else 0,
            "weighted_total_100": scientific.get("weighted_total_100", 0) if scientific else 0,
            "scientific_quality_band": scientific.get("scientific_quality_band", "INSUFFICIENT_EVIDENCE") if scientific else "INSUFFICIENT_EVIDENCE",
            "major_strengths": _semicolon_join(scientific.get("major_strengths", [])) if scientific else "INSUFFICIENT_EVIDENCE",
            "major_weaknesses": _semicolon_join(scientific.get("major_weaknesses", [])) if scientific else "INSUFFICIENT_EVIDENCE",
            "recommended_final_bucket": final.get("decision", "MANUAL_REVIEW"),
            "manual_review_needed": "YES" if final.get("manual_review") else "NO",
            "confidence_overall_100": _overall_confidence(phd, formal, thematic, mobility, scientific),
        })
    
    return pd.DataFrame(rows, columns=COLUMNS)


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Triage", index=False)
    return buf.getvalue()


def to_tsv(df: pd.DataFrame) -> str:
    return df.to_csv(sep="\t", index=False)
