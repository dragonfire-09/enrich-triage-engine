"""Excel + TSV export."""
import pandas as pd
import io
from typing import List, Dict


COLUMNS = [
    "filename", "decision", "primary_reason",
    "phd_found", "phd_date", "phd_confidence", "phd_evidence",
    "proposal_pages", "cv_pages", "formal_decision",
    "thematic_score", "thematic_decision", "thematic_hits",
    "mobility_turkey_months", "mobility_status", "mobility_evidence",
    "manual_review", "warnings"
]


def results_to_dataframe(results: List[Dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "filename": r.get("filename"),
            "decision": r.get("final", {}).get("decision"),
            "primary_reason": r.get("final", {}).get("primary_reason"),
            "phd_found": r.get("phd", {}).get("found"),
            "phd_date": str(r.get("phd", {}).get("date") or "INSUFFICIENT_EVIDENCE"),
            "phd_confidence": r.get("phd", {}).get("confidence"),
            "phd_evidence": (r.get("phd", {}).get("evidence_quote") or "")[:200],
            "proposal_pages": r.get("formal", {}).get("proposal_pages"),
            "cv_pages": r.get("formal", {}).get("cv_pages"),
            "formal_decision": r.get("formal", {}).get("decision"),
            "thematic_score": r.get("thematic", {}).get("score"),
            "thematic_decision": r.get("thematic", {}).get("decision"),
            "thematic_hits": ", ".join(
                r.get("thematic", {}).get("green_hits", []) +
                r.get("thematic", {}).get("blue_hits", [])
            ),
            "mobility_turkey_months": r.get("mobility", {}).get("turkey_months"),
            "mobility_status": r.get("mobility", {}).get("status"),
            "mobility_evidence": (r.get("mobility", {}).get("evidence") or "")[:200],
            "manual_review": r.get("final", {}).get("manual_review"),
            "warnings": "; ".join(r.get("formal", {}).get("warnings", []))
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Triage", index=False)
    return buf.getvalue()


def to_tsv(df: pd.DataFrame) -> str:
    return df.to_csv(sep="\t", index=False)
