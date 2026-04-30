"""PDF loading with OCR fallback."""
import pdfplumber
from typing import List, Dict
import io


def load_pdf(file_bytes: bytes, filename: str) -> Dict:
    """Load PDF and return per-page text + metadata."""
    pages = []
    total_chars = 0
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page_num": i + 1,
                    "text": text,
                    "char_count": len(text),
                    "needs_ocr": len(text.strip()) < 50
                })
                total_chars += len(text)
    except Exception as e:
        return {
            "filename": filename,
            "error": str(e),
            "pages": [],
            "page_count": 0,
            "total_chars": 0,
            "ocr_recommended": False
        }
    
    ocr_recommended = sum(1 for p in pages if p["needs_ocr"]) > len(pages) * 0.3
    
    return {
        "filename": filename,
        "pages": pages,
        "page_count": len(pages),
        "total_chars": total_chars,
        "ocr_recommended": ocr_recommended,
        "error": None
    }


def run_ocr_on_page(file_bytes: bytes, page_num: int, lang: str = "eng+tur") -> str:
    """OCR fallback for image-based pages."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        
        images = convert_from_bytes(file_bytes, first_page=page_num, last_page=page_num)
        if images:
            return pytesseract.image_to_string(images[0], lang=lang)
    except Exception as e:
        return f"[OCR_ERROR: {e}]"
    return ""


def get_full_text(pdf_data: Dict) -> str:
    """Concatenate all page text."""
    return "\n\n".join(p["text"] for p in pdf_data.get("pages", []))
