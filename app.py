"""ENRICH Triage Engine - Streamlit App."""
import streamlit as st
import pandas as pd
from datetime import datetime

from core.pdf_loader import load_pdf, get_full_text
from core.segmenter import segment_pages
from core.phd_extractor import extract_phd_evidence
from core.mobility_parser import parse_mobility
from core.thematic_scorer import score_thematic
from core.formal_checker import check_formal
from core.decision_engine import aggregate_decision
from exports.excel_writer import results_to_dataframe, to_xlsx_bytes, to_tsv

st.set_page_config(page_title="ENRICH Triage Engine", layout="wide", page_icon="🔬")

DEADLINE = datetime(2026, 4, 30, 17, 0)

st.title("🔬 ENRICH Triage Engine")
st.caption(f"📅 Deadline override: **30 April 2026, 17:00 (GMT+3, Türkiye)** — applies to PhD eligibility only")

with st.sidebar:
    st.header("⚙️ Calibration")
    st.caption("Codex notlarına göre kalibrasyon kontrolleri")
    
    thematic_doubt = st.slider("Thematic FAIL→DOUBT threshold", 0.0, 1.0, 0.3, 0.05)
    mobility_lookback = st.slider("Mobility lookback (years)", 1, 5, 3)
    show_raw_text = st.checkbox("Show raw extracted text (debug)")
    
    st.divider()
    st.markdown("**Deadline:** 30 Apr 2026 17:00 GMT+3")

uploaded = st.file_uploader(
    "📤 Upload 5–10 application PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    help="Per system rule: batch of 5 to 10 files"
)

if uploaded:
    if len(uploaded) > 10:
        st.error("Maximum 10 files per batch.")
        st.stop()
    if len(uploaded) < 1:
        st.warning("Please upload at least 1 file.")
        st.stop()
    
    st.success(f"✅ {len(uploaded)} file(s) loaded. Running triage…")
    
    results = []
    progress = st.progress(0)
    
    for idx, f in enumerate(uploaded):
        with st.spinner(f"Processing {f.name}…"):
            file_bytes = f.read()
            pdf_data = load_pdf(file_bytes, f.name)
            
            if pdf_data.get("error"):
                results.append({
                    "filename": f.name,
                    "error": pdf_data["error"],
                    "final": {"decision": "PARSE_ERROR", "primary_reason": pdf_data["error"], "manual_review": True}
                })
                progress.progress((idx + 1) / len(uploaded))
                continue
            
            spans = segment_pages(pdf_data["pages"])
            full_text = get_full_text(pdf_data)
            
            proposal_text = ""
            cv_text = ""
            if spans["proposal"]["found"]:
                s, e = spans["proposal"]["start_page"] - 1, spans["proposal"]["end_page"]
                proposal_text = "\n".join(p["text"] for p in pdf_data["pages"][s:e])
            if spans["cv"]["found"]:
                s, e = spans["cv"]["start_page"] - 1, spans["cv"]["end_page"]
                cv_text = "\n".join(p["text"] for p in pdf_data["pages"][s:e])
            
            phd = extract_phd_evidence(full_text, DEADLINE)
            formal = check_formal(spans, full_text)
            thematic = score_thematic(proposal_text or full_text)
            # NEW: pass full_text as fallback for mobility
            mobility = parse_mobility(cv_text, DEADLINE, mobility_lookback, full_text=full_text)
            final = aggregate_decision(phd, formal, thematic, mobility)
            
            results.append({
                "filename": f.name,
                "pdf_data": pdf_data,
                "spans": spans,
                "phd": phd,
                "formal": formal,
                "thematic": thematic,
                "mobility": mobility,
                "final": final,
                "ocr_recommended": pdf_data["ocr_recommended"]
            })
        progress.progress((idx + 1) / len(uploaded))
    
    progress.empty()
    
    st.header("📊 Batch Synthesis")
    decision_counts = {}
    for r in results:
        d = r["final"]["decision"]
        decision_counts[d] = decision_counts.get(d, 0) + 1
    
    cols = st.columns(len(decision_counts) or 1)
    for col, (k, v) in zip(cols, decision_counts.items()):
        col.metric(k, v)
    
    st.header("📋 Per-File Tabular Report")
    df = results_to_dataframe(results)
    st.dataframe(df, use_container_width=True)
    
    col_x, col_t = st.columns(2)
    with col_x:
        st.download_button(
            "💾 Download .xlsx",
            data=to_xlsx_bytes(df),
            file_name=f"enrich_triage_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col_t:
        with st.expander("📋 TSV (paste to Excel)"):
            st.code(to_tsv(df), language="tsv")
    
    st.header("🔍 Per-File Audit View")
    for r in results:
        with st.expander(f"**{r['filename']}** → `{r['final']['decision']}`"):
            if r.get("error"):
                st.error(r["error"])
                continue
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("📄 Segmentation")
                st.json(r["spans"])
                if r["ocr_recommended"]:
                    st.warning("⚠️ OCR may improve extraction (image-based pages detected)")
            with c2:
                st.subheader("🎓 PhD Evidence")
                st.json(r["phd"])
                st.subheader("📐 Formal")
                st.json(r["formal"])
            with c3:
                st.subheader("🌱 Thematic")
                st.json(r["thematic"])
                st.subheader("🌍 Mobility")
                st.json(r["mobility"])
            
            st.subheader("⚖️ Final Decision")
            st.json(r["final"])
            
            if show_raw_text:
                with st.expander("Raw extracted text"):
                    st.text_area("", get_full_text(r["pdf_data"])[:5000], height=300)
else:
    st.info("👆 Upload 5–10 PDF files to begin triage")
