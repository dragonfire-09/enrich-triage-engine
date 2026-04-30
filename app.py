"""ENRICH Triage Engine - Streamlit App (with Codex calibration panel)."""
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

# =====================================================================
# SIDEBAR — Codex Calibration Controls
# =====================================================================
with st.sidebar:
    st.header("⚙️ Calibration")
    st.caption("Codex notlarındaki 7 hata alanına karşılık gelen kontroller")
    
    with st.expander("ℹ️ Calibration Guide (oku)"):
        st.markdown("""
**Codex notları** parse + segmentation + evidence reconstruction kalibrasyonunda
şu 7 risk alanını işaretledi:

1. **Tek-PDF varsayımı** → multi-PDF dossier'ler
2. **Aggressive segmentation** → proposal/CV sınırları taşıyor
3. **Template contamination** → kapak/şablon sayfaları false positive
4. **PhD date dar regex** → görüntü/non-standart tarihler kaçırılıyor
5. **Mobility flexibility** → şehir/kurum bazlı timeline'lar
6. **Thematic too literal** → dolaylı transition mantığı kaçırılıyor
7. **Historical compatibility** → 2026 kuralları eski paketleri eziyor

Bu sliderlar her birini canlı olarak ayarlamanı sağlar.
Default değerler historical eligible 3 dosyada test edildi.
        """)
    
    st.divider()
    
    # ---- Codex #2: Segmentation page caps ----
    st.markdown("**📐 Codex #2 — Segmentation Caps**")
    proposal_cap = st.slider(
        "Proposal max pages",
        min_value=5, max_value=20, value=10, step=1,
        help="Hard cap. Segmenter bu sayıdan fazla sayfa atmaz. ENRICH default = 10."
    )
    cv_cap = st.slider(
        "CV max pages",
        min_value=3, max_value=15, value=5, step=1,
        help="Hard cap. ENRICH default = 5."
    )
    severe_overflow = st.slider(
        "Severe overflow factor (FAIL trigger)",
        min_value=1.0, max_value=3.0, value=1.5, step=0.1,
        help="Cap × bu çarpan = hard FAIL eşiği. 1.5 → proposal>15p hard fail."
    )
    
    st.divider()
    
    # ---- Codex #3: Template sensitivity ----
    st.markdown("**📋 Codex #3 — Template Contamination**")
    template_sensitivity = st.slider(
        "Template sensitivity",
        min_value=0.0, max_value=1.0, value=0.5, step=0.1,
        help="0 = ignore. 0.5 = standard. 1.0 = strict (lorem ipsum, TBD vb. aratılır)."
    )
    
    st.divider()
    
    # ---- Codex #5: Mobility ----
    st.markdown("**🌍 Codex #5 — Mobility**")
    mobility_lookback = st.slider(
        "Lookback (years)",
        min_value=1, max_value=5, value=3,
        help="Geriye kaç yıl tarayacağız. ENRICH default = 3."
    )
    max_turkey_months = st.slider(
        "Max Türkiye months (PASS threshold)",
        min_value=6, max_value=24, value=12, step=1,
        help="Lookback içinde Türkiye'de geçirilen max ay. > bu = DOUBT."
    )
    doubt_grace = st.slider(
        "DOUBT grace zone (months)",
        min_value=0, max_value=12, value=6, step=1,
        help="Threshold + bu kadar ay ek tolerans. Üzeri yine DOUBT (auto-FAIL yok)."
    )
    
    st.divider()
    
    # ---- Codex #6: Thematic ----
    st.markdown("**🌱 Codex #6 — Thematic**")
    thematic_pass = st.slider(
        "PASS threshold",
        min_value=0.4, max_value=0.9, value=0.6, step=0.05,
        help="Bu skorun üstü → PASS."
    )
    thematic_doubt = st.slider(
        "DOUBT threshold (FAIL→DOUBT geçişi)",
        min_value=0.0, max_value=0.5, value=0.3, step=0.05,
        help="Bu skorun üstü → DOUBT (FAIL değil). Codex: weak signals = manual review."
    )
    
    st.divider()
    
    # ---- Debug ----
    st.markdown("**🐛 Debug**")
    show_raw_text = st.checkbox(
        "Show raw extracted text",
        help="Audit view'da PDF'in çıkarılmış ham metnini göster."
    )
    
    st.divider()
    st.markdown("**📅 Deadline:** 30 Apr 2026 17:00 GMT+3")
    st.caption("Codex Rule A — applies to PhD eligibility only")

# =====================================================================
# MAIN — Codex Info Banner
# =====================================================================
with st.expander("📚 Codex Notları & Karar Mantığı", expanded=False):
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("""
### 🎯 Karar Tipleri
- ✅ **PASS** — tüm katmanlar geçti
- 🔴 **PHD_INELIGIBLE** — PhD/defense > deadline
- 🔴 **FAIL_FORMAL** — severe page overflow (segmenter başarısız)
- 🟠 **DOUBT** — thematic/mobility belirsiz, manual review
- 🟡 **INSUFFICIENT_EVIDENCE** — image-based PDF, OCR gerekli

### 🔬 Sıralı Pipeline
1. PDF Load → text + OCR-flag
2. Segmentation → Proposal/CV/Ethics page spans
3. PhD Eligibility → date vs deadline
4. Formal → page caps (max ≠ exact)
5. Thematic → Green/Blue with indirect-rescue
6. Mobility → Turkey months in lookback
7. Decision → öncelikli kural setine göre
        """)
    with col_right:
        st.markdown("""
### ⚖️ Codex Felsefesi
> "deterministic kontrolleri kodla yap; yorum gerektiren
> alanlarda otomatik ineligible yerine warning veya
> manual review sinyali üret"

### ✅ Hard FAIL ne zaman?
- PhD date > 30 Apr 2026 (Rule B)
- Segmenter başarısız (severe overflow)
- Thematic gerçekten 0 anchor + meaningful text

### 🟠 DOUBT ne zaman?
- Thematic borderline skor
- Mobility undated mentions
- CV bulundu ama thin

### 🟡 INSUFFICIENT_EVIDENCE ne zaman?
- CV image-based (OCR gerekli)
- PhD date hiç bulunamadı
- Proposal text < 300 char
        """)

# =====================================================================
# UPLOAD
# =====================================================================
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
            
            spans = segment_pages(pdf_data["pages"], proposal_cap=proposal_cap, cv_cap=cv_cap)
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
            formal = check_formal(
                spans, full_text,
                proposal_cap=proposal_cap, cv_cap=cv_cap,
                severe_overflow_factor=severe_overflow,
                template_sensitivity=template_sensitivity,
            )
            thematic = score_thematic(
                proposal_text or full_text,
                pass_threshold=thematic_pass,
                doubt_threshold=thematic_doubt,
            )
            mobility = parse_mobility(
                cv_text, DEADLINE,
                lookback_years=mobility_lookback,
                full_text=full_text,
                max_turkey_months=max_turkey_months,
                doubt_grace_months=doubt_grace,
            )
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
    
    # ============ AUDIT VIEW ============
    st.header("🔍 Per-File Audit View")
    for r in results:
        decision = r["final"]["decision"]
        emoji = {"PASS": "✅", "DOUBT": "🟠", "FAIL_FORMAL": "🔴",
                 "FAIL_THEMATIC": "🔴", "PHD_INELIGIBLE": "🔴",
                 "INSUFFICIENT_EVIDENCE": "🟡", "DOUBT_MOBILITY": "🟠",
                 "PARSE_ERROR": "⚫"}.get(decision, "⚪")
        with st.expander(f"{emoji} **{r['filename']}** → `{decision}`"):
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
    st.markdown("""
    ### 📖 Hızlı Başlangıç
    1. **Sol sidebar**'da kalibrasyon değerlerini gör (Codex 7 hata alanı)
    2. Yukarıdaki **Codex Notları** expander'ını oku (karar mantığı)
    3. **5–10 PDF** yükle (drag-and-drop veya Browse)
    4. Sonuçlar: Batch synthesis → Tablo → Per-file audit
    5. **Excel** veya **TSV** olarak indir
    
    ### ⚖️ Karar Felsefesi
    - **Hard FAIL** sadece deterministic ihlallerde (PhD date, severe overflow)
    - **DOUBT** → manual review için işaretlenir
    - **INSUFFICIENT_EVIDENCE** → OCR önerisi
    """
