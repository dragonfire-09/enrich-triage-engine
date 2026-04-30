"""ENRICH Triage Engine — Streamlit + OpenRouter LLM."""
import streamlit as st
import pandas as pd
from datetime import datetime

from core.pdf_loader import load_pdf, get_full_text
from core.segmenter import segment_pages
from core.metadata_extractor import extract_metadata
from core.phd_extractor import extract_phd_evidence
from core.mobility_parser import parse_mobility
from core.thematic_scorer import score_thematic
from core.formal_checker import check_formal
from core.scientific_assessor import assess_scientific_quality
from core.decision_engine import aggregate_decision
from exports.excel_writer import results_to_dataframe, to_xlsx_bytes, to_tsv

st.set_page_config(page_title="ENRICH Triage Engine", layout="wide", page_icon="🔬")

DEADLINE = datetime(2026, 4, 30, 17, 0)

st.title("🔬 ENRICH Triage Engine")
st.caption("📅 Deadline: **30 April 2026, 17:00 (GMT+3, Türkiye)** — applies to PhD eligibility only")

# =========================================================================
# SIDEBAR
# =========================================================================
with st.sidebar:
    st.header("⚙️ Calibration")
    
    with st.expander("ℹ️ Codex 7 Hata Alanı (oku)"):
        st.markdown("""
1. **Multi-PDF varsayımı** → batch upload
2. **Aggressive segmentation** → hard caps + boundary
3. **Template contamination** → soft warning
4. **PhD date dar regex** → multi-format + EN/TR
5. **Mobility flexibility** → 30+ TR token + fallback
6. **Thematic too literal** → DOUBT geçişi
7. **Historical compatibility** → 3 dosyada test edildi
        """)
    
    st.divider()
    st.markdown("**🤖 LLM Scientific Assessment**")
    
    enable_llm = st.checkbox("Enable LLM (OpenRouter)", value=True,
        help="Excellence/Impact/Implementation skorları için LLM kullan")
    
    if enable_llm:
        # API key — Secrets'tan veya manuel
        api_key = st.secrets.get("OPENROUTER_API_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = st.text_input("OpenRouter API Key", type="password",
                help="https://openrouter.ai/keys",
                placeholder="sk-or-v1-...")
        else:
            st.success("🔑 API key loaded from secrets")
        
        model = st.selectbox(
            "Model",
            options=[
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-exp:free",
                "meta-llama/llama-3.3-70b-instruct",
            ],
            index=0,
            help="Free için: gemini-2.0-flash-exp:free"
        )
    else:
        api_key = ""
        model = ""
    
    st.divider()
    st.markdown("**📐 Codex #2 — Segmentation**")
    proposal_cap = st.slider("Proposal max pages", 5, 20, 10)
    cv_cap = st.slider("CV max pages", 3, 15, 5)
    severe_overflow = st.slider("Severe overflow ×", 1.0, 3.0, 1.5, 0.1)
    
    st.divider()
    st.markdown("**📋 Codex #3 — Template**")
    template_sensitivity = st.slider("Template sensitivity", 0.0, 1.0, 0.5, 0.1)
    
    st.divider()
    st.markdown("**🌍 Codex #5 — Mobility**")
    mobility_lookback = st.slider("Lookback (years)", 1, 5, 3)
    max_turkey_months = st.slider("Max TR months (PASS)", 6, 24, 12)
    doubt_grace = st.slider("DOUBT grace (months)", 0, 12, 6)
    
    st.divider()
    st.markdown("**🌱 Codex #6 — Thematic**")
    thematic_pass = st.slider("PASS threshold", 0.4, 0.9, 0.6, 0.05)
    thematic_doubt = st.slider("DOUBT threshold", 0.0, 0.5, 0.3, 0.05)
    
    st.divider()
    show_raw_text = st.checkbox("🐛 Show raw extracted text")

# =========================================================================
# MAIN — Info Panel
# =========================================================================
with st.expander("📚 Karar Mantığı & Buckets", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
### 🎯 Bucket Öncelik Sırası
1. `PHD_UYUMSUZ` — date > deadline
2. `TEMATIK_UYUMSUZ` — score 0 + meaningful
3. `FORMAL_UYUMSUZ` — severe overflow
4. `MOBILITE_UYUMSUZ` — TR > 12 ay (gelecekte)
5. `MOBILITY_DOUBT` — undated mentions
6. `MANUAL_REVIEW` — INSUFFICIENT_EVIDENCE
7. `PASS` — tüm katmanlar geçti
        """)
    with c2:
        st.markdown("""
### ⚖️ Codex Felsefesi
> "Yorum gerektiren alanlarda otomatik ineligible
> ilan etmek yerine warning veya manual review
> sinyali üret."

### 🔬 Pipeline
1. PDF Load + OCR flag
2. Segmentation (hard caps)
3. Metadata extraction
4. PhD eligibility
5. Formal compliance
6. Thematic scoring
7. Mobility (window: 30 Apr 2023 → 30 Apr 2026)
8. Scientific quality (LLM)
9. Decision aggregation
        """)

# =========================================================================
# UPLOAD
# =========================================================================
uploaded = st.file_uploader(
    "📤 Upload 5–10 application PDFs",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded:
    if len(uploaded) > 10:
        st.error("Maximum 10 files per batch.")
        st.stop()
    
    if enable_llm and not api_key:
        st.warning("⚠️ LLM enabled but no API key — scientific scores will be 0. Disable LLM or provide a key.")
    
    st.success(f"✅ {len(uploaded)} file(s) loaded.")
    
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    for idx, f in enumerate(uploaded):
        status.info(f"Processing {f.name} ({idx+1}/{len(uploaded)})…")
        file_bytes = f.read()
        pdf_data = load_pdf(file_bytes, f.name)
        
        if pdf_data.get("error"):
            results.append({
                "filename": f.name,
                "error": pdf_data["error"],
                "metadata": {},
                "spans": {},
                "phd": {"found": False},
                "formal": {"decision": "FAIL", "issues": [pdf_data["error"]]},
                "thematic": {"decision": "INSUFFICIENT_EVIDENCE"},
                "mobility": {"status": "INSUFFICIENT_EVIDENCE"},
                "scientific": None,
                "final": {"decision": "MANUAL_REVIEW", "primary_reason": pdf_data["error"], "manual_review": True},
                "ocr_recommended": False,
            })
            progress.progress((idx + 1) / len(uploaded))
            continue
        
        spans = segment_pages(pdf_data["pages"], proposal_cap=proposal_cap, cv_cap=cv_cap)
        full_text = get_full_text(pdf_data)
        metadata = extract_metadata(full_text)
        
        proposal_text = ""
        cv_text = ""
        if spans["proposal"]["found"]:
            s, e = spans["proposal"]["start_page"] - 1, spans["proposal"]["end_page"]
            proposal_text = "\n".join(p["text"] for p in pdf_data["pages"][s:e])
        if spans["cv"]["found"]:
            s, e = spans["cv"]["start_page"] - 1, spans["cv"]["end_page"]
            cv_text = "\n".join(p["text"] for p in pdf_data["pages"][s:e])
        
        phd = extract_phd_evidence(full_text, DEADLINE)
        formal = check_formal(spans, full_text,
            proposal_cap=proposal_cap, cv_cap=cv_cap,
            severe_overflow_factor=severe_overflow,
            template_sensitivity=template_sensitivity)
        thematic = score_thematic(proposal_text or full_text,
            pass_threshold=thematic_pass,
            doubt_threshold=thematic_doubt)
        mobility = parse_mobility(cv_text, DEADLINE,
            lookback_years=mobility_lookback,
            full_text=full_text,
            max_turkey_months=max_turkey_months,
            doubt_grace_months=doubt_grace)
        
        # Scientific assessment (LLM)
        scientific = None
        if enable_llm and api_key:
            scientific = assess_scientific_quality(
                proposal_text or full_text[:10000],
                cv_text=cv_text,
                api_key=api_key,
                model=model,
            )
        
        final = aggregate_decision(phd, formal, thematic, mobility)
        
        results.append({
            "filename": f.name,
            "pdf_data": pdf_data,
            "metadata": metadata,
            "spans": spans,
            "phd": phd,
            "formal": formal,
            "thematic": thematic,
            "mobility": mobility,
            "scientific": scientific,
            "final": final,
            "ocr_recommended": pdf_data["ocr_recommended"]
        })
        progress.progress((idx + 1) / len(uploaded))
    
    progress.empty()
    status.empty()
    
    # ============ BATCH SYNTHESIS ============
    st.header("📊 Batch Synthesis")
    decision_counts = {}
    for r in results:
        d = r["final"]["decision"]
        decision_counts[d] = decision_counts.get(d, 0) + 1
    
    cols = st.columns(len(decision_counts) or 1)
    for col, (k, v) in zip(cols, decision_counts.items()):
        col.metric(k, v)
    
    manual_review_count = sum(1 for r in results if r["final"].get("manual_review"))
    if manual_review_count:
        st.warning(f"🔍 {manual_review_count} file(s) flagged for **manual review**")
    
    # ============ TABLE ============
    st.header("📋 Per-File Tabular Report (39 kolon)")
    df = results_to_dataframe(results)
    st.dataframe(df, use_container_width=True, height=400)
    
    cx, ct = st.columns(2)
    with cx:
        st.download_button(
            "💾 Download .xlsx",
            data=to_xlsx_bytes(df),
            file_name=f"enrich_triage_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with ct:
        with st.expander("📋 TSV (paste to Excel)"):
            st.code(to_tsv(df), language="tsv")
    
    # ============ PART 2 — File-by-File Notes ============
    st.header("📝 Part 2 — Dosya Bazlı Notlar")
    for i, r in enumerate(results, 1):
        sci = r.get("scientific") or {}
        decision = r["final"]["decision"]
        emoji = {"PASS": "✅", "MANUAL_REVIEW": "🟡", "MOBILITY_DOUBT": "🟠",
                 "PHD_UYUMSUZ": "🔴", "TEMATIK_UYUMSUZ": "🔴",
                 "FORMAL_UYUMSUZ": "🔴", "MOBILITE_UYUMSUZ": "🔴"}.get(decision, "⚪")
        
        with st.expander(f"{emoji} **{i}. {r['filename']}** → `{decision}`"):
            verdict = sci.get("one_paragraph_verdict") if sci else None
            if verdict and sci.get("llm_used"):
                st.markdown(f"**Verdict:** {verdict}")
            else:
                st.markdown(f"**Verdict:** {r['final']['primary_reason']}")
            
            cA, cB = st.columns(2)
            with cA:
                st.markdown("**Top 3 Strengths:**")
                strengths = sci.get("major_strengths") if sci else None
                if strengths and sci.get("llm_used"):
                    for s in strengths[:3]:
                        st.markdown(f"- {s}")
                else:
                    st.markdown("- _LLM disabled or no proposal text_")
            
            with cB:
                st.markdown("**Top 3 Weaknesses:**")
                weaknesses = sci.get("major_weaknesses") if sci else None
                if weaknesses and sci.get("llm_used"):
                    for w in weaknesses[:3]:
                        st.markdown(f"- {w}")
                else:
                    st.markdown("- _LLM disabled or no proposal text_")
            
            st.markdown(f"**Likely bucket:** `{decision}` — {r['final']['primary_reason']}")
            
            if sci and sci.get("rule_ambiguity") and sci["rule_ambiguity"] != "NONE":
                st.markdown(f"**⚠️ Rule ambiguity:** {sci['rule_ambiguity']}")
            if sci and sci.get("evidence_gaps") and sci["evidence_gaps"] != "NONE":
                st.markdown(f"**🔍 Evidence gaps:** {sci['evidence_gaps']}")
            
            # Detail panels
            st.divider()
            d1, d2, d3 = st.columns(3)
            with d1:
                st.subheader("📄 Segmentation")
                st.json(r["spans"])
            with d2:
                st.subheader("🎓 PhD")
                st.json(r["phd"])
                st.subheader("📐 Formal")
                st.json(r["formal"])
            with d3:
                st.subheader("🌱 Thematic")
                st.json(r["thematic"])
                st.subheader("🌍 Mobility")
                st.json(r["mobility"])
            
            if sci:
                st.subheader("🔬 Scientific Quality (LLM)")
                st.json(sci)
            
            if show_raw_text and r.get("pdf_data"):
                with st.expander("Raw extracted text"):
                    st.text_area("", get_full_text(r["pdf_data"])[:5000], height=300)
    
    # ============ PART 3 — Batch Synthesis Detailed ============
    st.header("🔎 Part 3 — Batch Sentezi")
    
    # Strongest / weakest files by weighted_total_100
    scored = [(r, (r.get("scientific") or {}).get("weighted_total_100", 0)) for r in results]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown("**💪 En Güçlü Dosyalar** (weighted_total_100)")
        for r, sc in scored[:3]:
            st.markdown(f"- `{r['filename']}` → **{sc}** ({(r.get('scientific') or {}).get('scientific_quality_band','?')})")
    with cs2:
        st.markdown("**📉 En Zayıf Dosyalar**")
        for r, sc in scored[-3:][::-1]:
            st.markdown(f"- `{r['filename']}` → **{sc}** ({(r.get('scientific') or {}).get('scientific_quality_band','?')})")
    
    st.markdown("**📊 Bucket Dağılımı**")
    bucket_df = pd.DataFrame(list(decision_counts.items()), columns=["Bucket", "Count"])
    st.dataframe(bucket_df, use_container_width=True)
    
    # Common issues
    st.markdown("**🔍 Manual Review Gerektiren Dosyalar**")
    for r in results:
        if r["final"].get("manual_review"):
            st.markdown(f"- `{r['filename']}` → {r['final']['primary_reason']}")
    
    # ============ PART 4 — Strict QA Check ============
    st.header("🚨 Part 4 — Strict QA Check")
    
    qa_findings = []
    
    # Formally compliant but scientifically weak
    for r in results:
        sci = r.get("scientific") or {}
        if (r["formal"].get("decision") == "PASS" 
            and sci.get("scientific_quality_band") in ("WEAK", "VERY_WEAK")):
            qa_findings.append(("formally_ok_but_scientifically_weak", r["filename"]))
    
    # Thematically OK but mobility risky
    for r in results:
        if (r["thematic"].get("decision") in ("PASS", "DOUBT")
            and r["mobility"].get("status") == "DOUBT"):
            qa_findings.append(("thematic_ok_but_mobility_risky", r["filename"]))
    
    # Page-count borderline
    for r in results:
        pp = r["formal"].get("proposal_pages", 0)
        cp = r["formal"].get("cv_pages", 0)
        if pp < 5 or cp < 3:
            qa_findings.append(("short_but_compliant_might_misjudge", r["filename"]))
    
    # Template contamination
    for r in
