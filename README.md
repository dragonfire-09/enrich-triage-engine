# 🔬 ENRICH Triage Engine

> **TÜBİTAK 2236-A ENRICH başvurularını otomatik tarayan, LLM-destekli triage motoru.**  
> Streamlit + OpenRouter LLM + 7-katmanlı karar mantığı = Production-ready akademik başvuru elemesi.

[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B?logo=streamlit)](https://streamlit.io/cloud)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 Ne Yapar?

ENRICH Triage Engine, akademik başvuru PDF'lerini (5–10 dosyalık batch'ler halinde) otomatik olarak inceler ve 7 katmanlı karar zinciriyle her dosyaya bir **bucket** atar:

| Bucket | Anlamı |
|--------|--------|
| ✅ `PASS` | Tüm katmanlardan geçti — değerlendirmeye uygun |
| 🟡 `MANUAL_REVIEW` | İnsan değerlendirmesi gerekiyor |
| 🟠 `MOBILITY_DOUBT` | Hareketlilik şüpheli (Türkiye'de 12+ ay) |
| 🔴 `PHD_UYUMSUZ` | Doktora tarihi deadline'dan sonra |
| 🔴 `TEMATIK_UYUMSUZ` | Green/Blue Transition ile alakasız |
| 🔴 `FORMAL_UYUMSUZ` | Sayfa limitleri ciddi şekilde aşılmış |
| 🔴 `MOBILITE_UYUMSUZ` | Türkiye'de geçen süre limit aşımı |

Her dosya için **39 sütunluk detaylı rapor**, **Türkçe narrative verdict**, ve **LLM-tabanlı bilimsel kalite skoru** üretir.

---

## 🏗️ Mimari

```mermaid
flowchart TD
    A[📤 PDF Batch Upload] --> B[📄 PDF Loader + OCR Flag]
    B --> C[✂️ Segmenter<br/>Proposal/CV split]
    C --> D[🆔 Metadata Extractor<br/>Regex-based]
    C --> E[🎓 PhD Eligibility<br/>Multi-format date]
    C --> F[📐 Formal Compliance<br/>Page caps]
    C --> G[🌱 Thematic Scoring<br/>Green+Blue+Indirect]
    C --> H[🌍 Mobility Parser<br/>3-yr window]
    C --> I[🤖 LLM Scientific Assessment<br/>OpenRouter]
    D --> J[⚖️ Decision Engine<br/>Bucket Aggregation]
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K[📊 39-Column Report]
    J --> L[📝 Türkçe Verdict]
    J --> M[🚨 QA Strict Check]
