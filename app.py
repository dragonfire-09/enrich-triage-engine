"""ENRICH Triage Engine — Streamlit + OpenRouter LLM (Modern UI v2.1)."""
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

# =========================================================================
# PAGE CONFIG
# =========================================================================
st.set_page_config(
    page_title="ENRICH Triage Engine",
    layout="wide",
    page_icon="🔬",
    initial_sidebar_state="expanded",
)

DEADLINE = datetime(2026, 4, 30, 17, 0)

# =========================================================================
# 🎨 MODERN CSS — Gradient header, cards, badges, hover effects
# =========================================================================
st.markdown("""
<style>
    /* Hide Streamlit default header/footer for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Gradient header card */
    .hero-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.25);
        margin-bottom: 1.5rem;
        color: white;
    }
    .hero-card h1 {
        font-size: 2.4rem;
        margin: 0 0 0.5rem 0;
        font-weight: 800;
        color: white;
    }
    .hero-card p {
        font-size: 1.05rem;
        opacity: 0.95;
        margin: 0.3rem 0;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        backdrop-filter: blur(10px);
    }
    
    /* Modern bucket badges */
    .bucket-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    .bucket-pass { background: linear-gradient(135deg, #10b981, #059669); color: white; }
    .bucket-manual { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }
    .bucket-mobility { background: linear-gradient(135deg, #f97316, #ea580c); color: white; }
    .bucket-fail { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
    
    /* Stat cards */
    .stat-card {
        background: white;
        padding: 1.2rem 1.5rem;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    .stat-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin: 0;
    }
    
    /* Modern primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border: none;
        border-radius: 12px;
        padding: 0.7rem 2rem;
        font-weight: 700;
        font-size: 1rem;
        box-shadow: 0 4px 14px rgba(102, 126, 234, 0.35);
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* Danger button (clear/reset) */
    .danger-btn button {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
    }
    
    /* File card */
    .file-card {
        background: #f9fafb;
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.4rem 0;
        font-family: 'Monaco', monospace;
        font-size: 0.9rem;
    }
    
    /* Section dividers */
    .section-header {
        background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
        padding: 0.8rem 1.5rem;
        border-radius: 10px;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* Smooth animation */
    [data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
    }
    [data-testid="stExpander"]:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar polish */
    [data-testid="stSidebar"] {
        background: #fafbfc;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# 🎨 HERO HEADER
# =========================================================================
st.markdown(f"""
<div class="hero-card">
    <h1>🔬 ENRICH Triage Engine</h1>
    <p>Akademik başvuruları akıllıca eleyen, LLM-destekli triage motoru</p>
    <div style="margin-top: 1rem;">
        <span class="hero-badge">📅 Deadline: 30 April 2026, 17:00 (GMT+3)</span>
        <span class="hero-badge">🌍 Horizon Europe Aligned</span>
        <span class="hero-badge">🇹🇷 TÜBİTAK 2236-A</span>
    </div>
</div>
""", unsafe_allow_html=True)


# =========================================================================
# SESSION STATE — Sonuçları sakla
# =========================================================================
if "results" not in st.session_state:
    st.session_state.results = None
if "uploaded_files_meta" not in st.session_state:
    st.session_state.uploaded_files_meta = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False


def reset_analysis():
    """Tüm session state'i temizle."""
    st.session_state.results = None
    st.session_state.uploaded_files_meta = []
    st.session_state.analysis_done = False


# =========================================================================
# SIDEBAR — Calibration
# =========================================================================
with st.sidebar:
    st.markdown("### ⚙️ Calibration")
    
    with st.expander("ℹ️ Codex 7 Hata Alanı"):
        st.markdown("""
1. **Multi-PDF varsayımı** → batch upload  
2. **Aggressive segmentation** → hard caps  
3. **Template contamination** → soft warning  
4. **PhD date dar regex** → multi-format  
5. **Mobility flexibility** → 30+ TR token  
6. **Thematic too literal** → DOUBT geçişi  
7. **Historical compatibility** → tested  
        """)
    
    st.divider()
    st.markdown("**🤖 LLM Scientific Assessment**")
    enable_llm = st.checkbox("Enable LLM (OpenRouter)", value=True)
    
    api_key = ""
    model = ""
    if enable_llm:
        try:
            api_key = st.secrets.get("OPENROUTER_API_KEY", "")
        except Exception:
            api_key = ""
        if not api_key:
            api_key = st.text_input("OpenRouter API Key", type="password",
                placeholder="sk-or-v1-...")
            if api_key:
                st.success(f"🔑 Manual key (len: {len(api_key)})")
        else:
            st.success(f"🔑 Secrets key loaded ({len(api_key)})")
        model = st.selectbox("Model", [
            "openai/gpt-4o-mini", "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.3-70b-instruct",
        ])
    
    st.divider()
    st.markdown("**📐 Segmentation**")
    proposal_cap = st.slider("Proposal max pages", 5, 20, 10)
    cv_cap = st.slider("CV max pages", 3, 15, 5)
    severe_overflow = st.slider("Severe overflow ×", 1.0, 3.0, 1.5, 0.1)
    
    st.divider()
    st.markdown("**📋 Template**")
    template_sensitivity = st.slider("Template sensitivity", 0.0, 1.0, 0.5, 0.1)
    
    st.divider()
    st.markdown("**🌍 Mobility**")
    mobility_lookback = st.slider("Lookback (years)", 1, 5, 3)
    max_turkey_months = st.slider("Max TR months", 6, 24, 12)
    doubt_grace = st.slider("DOUBT grace", 0, 12, 6)
    
    st.divider()
    st.markdown("**🌱 Thematic**")
    thematic_pass = st.slider("PASS threshold", 0.4, 0.9, 0.6, 0.05)
    thematic_doubt = st.slider("DOUBT threshold", 0.0, 0.5, 0.3, 0.05)
    
    st.divider()
    show_raw_text = st.checkbox("🐛 Show raw text")
    
    # ─── Reset Button (sadece analiz tamamlandıysa) ───
    if st.session_state.analysis_done:
        st.divider()
        st.markdown("### 🔄 Yeni Analiz")
        if st.button(
            "🗑️ Temizle ve Yeni Analiz Başlat",
            use_container_width=True,
            type="secondary",
            help="Mevcut sonuçları sil, yeni batch yükle"
        ):
            reset_analysis()
            st.rerun()


# =========================================================================
# INFO PANEL
# =========================================================================
with st.expander("📚 Karar Mantığı & Buckets", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
### 🎯 Bucket Öncelik Sırası
1. `PHD_UYUMSUZ` — date > deadline
2. `TEMATIK_UYUMSUZ` — score 0
3. `FORMAL_UYUMSUZ` — severe overflow
4. `MOBILITE_UYUMSUZ` — TR > 12 ay
5. `MOBILITY_DOUBT` — undated mentions
6. `MANUAL_REVIEW` — INSUFFICIENT / WEAK
7. `PASS` — tüm katmanlar geçti
        """)
    with c2:
        st.markdown("""
### ⚖️ Codex Felsefesi
> "Yorum gerektiren alanlarda otomatik
> ineligible ilan etmek yerine warning
> veya manual review sinyali üret."

### 🔬 Pipeline (9-step)
PDF → Segmentation → Metadata → PhD →
Formal → Thematic → Mobility →
LLM Quality → Decision Aggregation
        """)


# =========================================================================
# 🚀 EĞER ANALİZ TAMAMLANMADIYSA → UPLOAD + ANALYZE FLOW
# =========================================================================
if not st.session_state.analysis_done:
    
    st.markdown('<div class="section-header">📤 PDF Yükleme</div>', unsafe_allow_html=True)
    
    uploaded = st.file_uploader(
        "Upload 5–10 application PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    
    if uploaded:
        if len(uploaded) > 10:
            st.error("⚠️ Maximum 10 files per batch.")
            st.stop()
        
        # ─── Pre-flight Display ───
        st.success(f"✅ {len(uploaded)} dosya yüklendi.")
        
        with st.expander("📁 Yüklenen Dosyalar", expanded=True):
            total_size = 0
            for i, f in enumerate(uploaded, 1):
                size_mb = f.size / (1024 * 1024)
                total_size += size_mb
                st.markdown(
                    f'<div class="file-card"><b>{i}.</b> {f.name} '
                    f'<span style="color:#6b7280;float:right;">{size_mb:.1f} MB</span></div>',
                    unsafe_allow_html=True
                )
            st.caption(f"📊 Toplam: {len(uploaded)} dosya, {total_size:.1f} MB")
        
        # LLM status
        if enable_llm and not api_key:
            st.warning("⚠️ LLM açık ama API key yok — scientific scores 0 olacak.")
        elif enable_llm and api_key:
            est_low = len(uploaded) * 5
            est_high = len(uploaded) * 15
            st.info(f"🤖 LLM hazır: `{model}` — Tahmini süre: ~{est_low}-{est_high} sn")
        else:
            st.info("ℹ️ LLM kapalı — sadece deterministic katmanlar çalışacak.")
        
        with st.expander("⚙️ Aktif Kalibrasyon Özeti"):
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.markdown(f"""
**📐 Segmentation**
- Proposal: `{proposal_cap}p`
- CV: `{cv_cap}p`
- Overflow: `{severe_overflow}×`
                """)
            with cc2:
                st.markdown(f"""
**🌍 Mobility**
- Lookback: `{mobility_lookback}y`
- Max TR: `{max_turkey_months}mo`
- Grace: `{doubt_grace}mo`
                """)
            with cc3:
                st.markdown(f"""
**🌱 Thematic**
- PASS: `{thematic_pass}`
- DOUBT: `{thematic_doubt}`
- Template: `{template_sensitivity}`
                """)
        
        # ─── Analize Başla Button ───
        st.markdown("<br>", unsafe_allow_html=True)
        bcol1, bcol2, bcol3 = st.columns([1, 2, 1])
        with bcol2:
            start_analysis = st.button(
                "🚀 Analize Başla",
                type="primary",
                use_container_width=True,
            )
        
        if not start_analysis:
            st.info("👆 Buton'a basana kadar LLM tokenları harcanmaz. "
                    "Calibration slider'larını sidebar'dan ayarlayabilirsin.")
            st.stop()
        
        # ─── PIPELINE EXECUTION ───
        results = []
        progress = st.progress(0)
        status = st.empty()
        
        for idx, f in enumerate(uploaded):
            status.info(f"⏳ {f.name} ({idx+1}/{len(uploaded)}) işleniyor…")
            file_bytes = f.read()
            pdf_data = load_pdf(file_bytes, f.name)
            
            if pdf_data.get("error"):
                results.append({
                    "filename": f.name, "error": pdf_data["error"],
                    "metadata": {}, "spans": {},
                    "phd": {"found": False},
                    "formal": {"decision": "FAIL", "issues": [pdf_data["error"]],
                               "warnings": [], "proposal_pages": 0, "cv_pages": 0},
                    "thematic": {"decision": "INSUFFICIENT_EVIDENCE", "score": 0,
                                 "green_hits": [], "blue_hits": [], "indirect_hits": [],
                                 "evidence": pdf_data["error"]},
                    "mobility": {"status": "INSUFFICIENT_EVIDENCE", "evidence": pdf_data["error"]},
                    "scientific": None,
                    "final": {"decision": "MANUAL_REVIEW",
                              "primary_reason": pdf_data["error"], "manual_review": True},
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
            
            scientific = None
            if enable_llm and api_key:
                with st.spinner(f"🤖 LLM assessing {f.name}…"):
                    scientific = assess_scientific_quality(
                        proposal_text or full_text[:10000],
                        cv_text=cv_text, api_key=api_key, model=model,
                    )
                    if scientific.get("llm_error"):
                        st.error(f"LLM error for {f.name}: {scientific['llm_error']}")
            
            final = aggregate_decision(
                phd, formal, thematic, mobility,
                scientific={
                    "band": (scientific or {}).get("scientific_quality_band"),
                    "weighted_total_100": (scientific or {}).get("weighted_total_100", 0),
                } if scientific else None,
            )
            
            results.append({
                "filename": f.name, "pdf_data": pdf_data, "metadata": metadata,
                "spans": spans, "phd": phd, "formal": formal,
                "thematic": thematic, "mobility": mobility,
                "scientific": scientific, "final": final,
                "ocr_recommended": pdf_data["ocr_recommended"]
            })
            progress.progress((idx + 1) / len(uploaded))
        
        progress.empty()
        status.empty()
        
        # Save to session state
        st.session_state.results = results
        st.session_state.analysis_done = True
        st.rerun()
    
    else:
        # No upload yet
        st.info("👆 Yukarıdan **5-10 PDF** yükleyerek triage'a başla.")


# =========================================================================
# 📊 EĞER ANALİZ TAMAMLANDIYSA → SONUÇLARI GÖSTER
# =========================================================================
else:
    results = st.session_state.results
    
    # ─── Success banner with reset hint ───
    col_success, col_reset = st.columns([3, 1])
    with col_success:
        st.success(f"✅ Analiz tamamlandı — **{len(results)} dosya** işlendi")
    with col_reset:
        if st.button(
            "🗑️ Yeni Analiz",
            use_container_width=True,
            help="Mevcut sonuçları sil, yeni batch için temizle"
        ):
            reset_analysis()
            st.rerun()
    
    # ─── Bucket Stats with Modern Cards ───
    st.markdown('<div class="section-header">📊 Batch Synthesis</div>', unsafe_allow_html=True)
    
    decision_counts = {}
    for r in results:
        d = r["final"]["decision"]
        decision_counts[d] = decision_counts.get(d, 0) + 1
    
    # Render stat cards
    cols = st.columns(max(len(decision_counts), 1))
    for col, (k, v) in zip(cols, decision_counts.items()):
        # Renk seçimi bucket'a göre
        if k == "PASS":
            color = "#10b981"
        elif k in ("MANUAL_REVIEW", "MOBILITY_DOUBT"):
            color = "#f59e0b"
        else:
            color = "#ef4444"
        
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-label">{k.replace('_', ' ')}</p>
                <p class="stat-value" style="background: linear-gradient(135deg, {color}, {color}dd); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{v}</p>
            </div>
            """, unsafe_allow_html=True)
    
    manual_count = sum(1 for r in results if r["final"].get("manual_review"))
    if manual_count:
        st.warning(f"🔍 **{manual_count} dosya** manuel review için işaretlendi")
    
    # ─── Part 1 — Tabular Report ───
    st.markdown('<div class="section-header">📋 Part 1 — Per-File Tabular Report (39 columns)</div>',
                unsafe_allow_html=True)
    df = results_to_dataframe(results)
    st.dataframe(df, use_container_width=True, height=400)
    
    cx, ct = st.columns(2)
    with cx:
        st.download_button(
            "💾 Download .xlsx",
            data=to_xlsx_bytes(df),
            file_name=f"enrich_triage_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with ct:
        with st.expander("📋 TSV (paste to Excel)"):
            st.code(to_tsv(df), language="tsv")
    
    # ─── Part 2 — File-by-File Notes ───
    st.markdown('<div class="section-header">📝 Part 2 — Dosya Bazlı Notlar</div>',
                unsafe_allow_html=True)
    
    for i, r in enumerate(results, 1):
        sci = r.get("scientific") or {}
        decision = r["final"]["decision"]
        emoji_map = {"PASS": "✅", "MANUAL_REVIEW": "🟡", "MOBILITY_DOUBT": "🟠",
                     "PHD_UYUMSUZ": "🔴", "TEMATIK_UYUMSUZ": "🔴",
                     "FORMAL_UYUMSUZ": "🔴", "MOBILITE_UYUMSUZ": "🔴"}
        emoji = emoji_map.get(decision, "⚪")
        
        with st.expander(f"{emoji}  **{i}. {r['filename']}** → `{decision}`"):
            verdict = sci.get("one_paragraph_verdict") if sci else None
            if verdict and sci.get("llm_used"):
                st.markdown(f"**📜 Verdict:** {verdict}")
            else:
                st.markdown(f"**📜 Verdict:** {r['final']['primary_reason']}")
            
            cA, cB = st.columns(2)
            with cA:
                st.markdown("**💪 Top 3 Strengths**")
                strengths = sci.get("major_strengths") if sci else None
                if strengths and sci.get("llm_used"):
                    for s in strengths[:3]:
                        st.markdown(f"- {s}")
                else:
                    st.markdown("- _LLM disabled_")
            with cB:
                st.markdown("**⚠️ Top 3 Weaknesses**")
                weaknesses = sci.get("major_weaknesses") if sci else None
                if weaknesses and sci.get("llm_used"):
                    for w in weaknesses[:3]:
                        st.markdown(f"- {w}")
                else:
                    st.markdown("- _LLM disabled_")
            
            st.markdown(f"**🎯 Bucket:** `{decision}` — {r['final']['primary_reason']}")
            
            if sci and sci.get("rule_ambiguity") and sci["rule_ambiguity"] != "NONE":
                st.info(f"⚠️ **Rule ambiguity:** {sci['rule_ambiguity']}")
            if sci and sci.get("evidence_gaps") and sci["evidence_gaps"] != "NONE":
                st.info(f"🔍 **Evidence gaps:** {sci['evidence_gaps']}")
            
            st.divider()
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown("**📄 Segmentation**")
                st.json(r["spans"])
                st.markdown("**🆔 Metadata**")
                st.json(r.get("metadata", {}))
            with d2:
                st.markdown("**🎓 PhD**")
                st.json(r["phd"])
                st.markdown("**📐 Formal**")
                st.json(r["formal"])
            with d3:
                st.markdown("**🌱 Thematic**")
                st.json(r["thematic"])
                st.markdown("**🌍 Mobility**")
                st.json(r["mobility"])
            
            if sci:
                st.markdown("**🔬 Scientific Quality (LLM)**")
                st.json(sci)
            
            if show_raw_text and r.get("pdf_data"):
                with st.expander("📄 Raw extracted text"):
                    st.text_area("", get_full_text(r["pdf_data"])[:5000], height=300)
    
    # ─── Part 3 — Batch Synthesis ───
    st.markdown('<div class="section-header">🔎 Part 3 — Batch Sentezi</div>',
                unsafe_allow_html=True)
    
    scored = [(r, (r.get("scientific") or {}).get("weighted_total_100", 0)) for r in results]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown("**💪 En Güçlü Dosyalar** (weighted_total_100)")
        for r, sc in scored[:3]:
            band = (r.get("scientific") or {}).get("scientific_quality_band", "?")
            st.markdown(f"- `{r['filename']}` → **{sc}** ({band})")
    with cs2:
        st.markdown("**📉 En Zayıf Dosyalar**")
        for r, sc in scored[-3:][::-1]:
            band = (r.get("scientific") or {}).get("scientific_quality_band", "?")
            st.markdown(f"- `{r['filename']}` → **{sc}** ({band})")
    
    st.markdown("**📊 Bucket Dağılımı**")
    bucket_df = pd.DataFrame(list(decision_counts.items()), columns=["Bucket", "Count"])
    st.dataframe(bucket_df, use_container_width=True)
    
    # Common issues
    formal_issues_all = []
    for r in results:
        formal_issues_all.extend(r["formal"].get("warnings", []) + r["formal"].get("issues", []))
    if formal_issues_all:
        st.markdown("**⚠️ Tekrar Eden Formal Sorunlar**")
        from collections import Counter
        for issue, cnt in Counter(formal_issues_all).most_common(5):
            st.markdown(f"- {issue} ({cnt} dosya)")
    
    thematic_fails = [r["filename"] for r in results if r["thematic"].get("decision") == "FAIL"]
    thematic_doubts = [r["filename"] for r in results if r["thematic"].get("decision") == "DOUBT"]
    if thematic_fails or thematic_doubts:
        st.markdown("**🌱 Tematik Sorunlar**")
        if thematic_fails:
            st.markdown(f"- FAIL ({len(thematic_fails)}): {', '.join(thematic_fails)}")
        if thematic_doubts:
            st.markdown(f"- DOUBT ({len(thematic_doubts)}): {', '.join(thematic_doubts)}")
    
    mob_doubts = [r["filename"] for r in results if r["mobility"].get("status") == "DOUBT"]
    mob_insuff = [r["filename"] for r in results if r["mobility"].get("status") == "INSUFFICIENT_EVIDENCE"]
    if mob_doubts or mob_insuff:
        st.markdown("**🌍 Mobility Sorunları**")
        if mob_doubts:
            st.markdown(f"- DOUBT ({len(mob_doubts)}): {', '.join(mob_doubts)}")
        if mob_insuff:
            st.markdown(f"- INSUFFICIENT ({len(mob_insuff)}): {', '.join(mob_insuff)}")
    
    st.markdown("**🔍 Manual Review Gerektiren Dosyalar**")
    manual_files = [r for r in results if r["final"].get("manual_review")]
    if manual_files:
        for r in manual_files:
            st.markdown(f"- `{r['filename']}` → {r['final']['primary_reason']}")
    else:
        st.markdown("_Hiçbir dosya manuel review gerektirmiyor._")
    
    # ─── Part 4 — QA Check ───
    st.markdown('<div class="section-header">🚨 Part 4 — Strict QA Check</div>',
                unsafe_allow_html=True)
    
    qa_findings = {
        "formally_ok_but_scientifically_weak": [],
        "thematic_ok_but_mobility_risky": [],
        "short_but_compliant_might_misjudge": [],
        "template_contamination": [],
    }
    
    for r in results:
        sci = r.get("scientific") or {}
        if (r["formal"].get("decision") == "PASS"
            and sci.get("scientific_quality_band") in ("WEAK", "VERY_WEAK")
            and sci.get("llm_used")):
            qa_findings["formally_ok_but_scientifically_weak"].append(r["filename"])
        if (r["thematic"].get("decision") in ("PASS", "DOUBT")
            and r["mobility"].get("status") == "DOUBT"):
            qa_findings["thematic_ok_but_mobility_risky"].append(r["filename"])
        pp = r["formal"].get("proposal_pages", 0)
        cp = r["formal"].get("cv_pages", 0)
        if (pp > 0 and pp < 5) or (cp > 0 and cp < 3):
            qa_findings["short_but_compliant_might_misjudge"].append(
                f"{r['filename']} (proposal={pp}p, cv={cp}p)"
            )
        if any("Template" in w for w in r["formal"].get("warnings", [])):
            qa_findings["template_contamination"].append(r["filename"])
    
    qa_questions = [
        ("Did any file look formally compliant but scientifically weak?",
         "formally_ok_but_scientifically_weak"),
        ("Did any file look thematically acceptable but mobility-risky?",
         "thematic_ok_but_mobility_risky"),
        ("Did any file risk a false rejection due to 'exact pages' misreading?",
         "short_but_compliant_might_misjudge"),
        ("Did any file show template contamination or packaging inconsistency?",
         "template_contamination"),
    ]
    
    for question, key in qa_questions:
        files = qa_findings[key]
        st.markdown(f"**{question}**")
        if files:
            st.warning(f"⚠️ YES — {len(files)} dosya:")
            for fn in files:
                st.markdown(f"  - `{fn}`")
        else:
            st.success("✅ NO — bu kategoride sorunlu dosya yok")
        st.divider()
    
    # ─── Bottom: Big Reset Button ───
    st.markdown("<br>", unsafe_allow_html=True)
    rcol1, rcol2, rcol3 = st.columns([1, 2, 1])
    with rcol2:
        if st.button(
            "🔄 Yeni Batch için Temizle",
            use_container_width=True,
            type="primary",
            help="Sonuçları sil, yeni dosya yüklemeye dön"
        ):
            reset_analysis()
            st.rerun()
