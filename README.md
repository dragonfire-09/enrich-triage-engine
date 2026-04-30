# 🔬 ENRICH Triage Engine

ENRICH-benzeri başvuru dosyaları için ilk aşama idari/tematik triage motoru.
Streamlit tabanlı, audit edilebilir, kalibre edilebilir.

> **Felsefe:** Deterministic kontrolleri kodla yap; yorum gerektiren alanlarda
> otomatik ineligible yerine **warning** veya **manual review** sinyali üret.

---

## 🎯 Ne Yapar?

5–10 application PDF'i yükle → her biri için:

1. **PDF Load** — text extraction + OCR-recommendation flag
2. **Segmentation** — Proposal / CV / Ethics page spans (hard caps ile)
3. **PhD Eligibility** — date extraction vs. deadline (30 Apr 2026)
4. **Formal Compliance** — page limits + template contamination
5. **Thematic Scoring** — Green/Blue Transition (indirect-rescue)
6. **Mobility** — Türkiye months in last N years
7. **Decision Aggregation** — PASS / DOUBT / FAIL / INSUFFICIENT_EVIDENCE

Çıktı: 1 satır per file Excel (`.xlsx`) + TSV + per-file audit JSON.

---

## 📊 Karar Tipleri

| Karar | Anlamı | Manual Review? |
|---|---|:---:|
| ✅ `PASS` | Tüm katmanlar geçti | ❌ |
| 🔴 `PHD_INELIGIBLE` | PhD/defense > deadline | ❌ |
| 🔴 `FAIL_FORMAL` | Severe page overflow (segmenter başarısız) | ❌ |
| 🔴 `FAIL_THEMATIC` | Proposal'da hiç anchor yok | ✅ |
| 🟠 `DOUBT` | Thematic / mobility borderline | ✅ |
| 🟡 `INSUFFICIENT_EVIDENCE` | Image-based PDF, OCR gerekli | ✅ |
| ⚫ `PARSE_ERROR` | PDF okunamadı | ✅ |

---

## ⚙️ Codex 7 Hata Alanı — Kalibrasyon Kontrolleri

Codex notları parse + segmentation + evidence reconstruction kalibrasyonunda
şu 7 risk alanını işaretledi. Sol sidebar'daki sliderlar bunlara denk gelir:

| # | Hata Alanı | Sidebar Kontrolü | Çözüm |
|---|---|---|---|
| 1 | Tek-PDF varsayımı | (multi-file uploader) | Çözüldü — batch upload |
| 2 | Aggressive segmentation | Proposal/CV cap, severe overflow | Hard caps + boundary detection |
| 3 | Template contamination | Template sensitivity | Sensitivity-controlled markers |
| 4 | PhD date dar regex | (kod-içi) | Multi-format + EN/TR keywords |
| 5 | Mobility flexibility | Lookback, max months, grace | 30+ TR token + full-text fallback |
| 6 | Thematic too literal | Pass / doubt threshold | Indirect-rescue + DOUBT geçişi |
| 7 | Historical compatibility | (default değerler) | 3 historical dosyada test edildi |

---

## 🚀 Deploy

### Streamlit Community Cloud
1. Bu repo'yu fork et veya kullan
2. https://share.streamlit.io → Continue with GitHub
3. New app → bu repo, branch `main`, main file `app.py`
4. Deploy

### Local Çalıştırma
```bash
git clone https://github.com/<username>/enrich-triage-engine.git
cd enrich-triage-engine

# Sistem paketleri (Tesseract OCR + Poppler)
sudo apt-get install tesseract-ocr tesseract-ocr-tur poppler-utils

# Python paketleri
pip install -r requirements.txt

# Çalıştır
streamlit run app.py
