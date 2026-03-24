from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

PDF_TEXT_MIN_WORDS = int(os.getenv("PDF_TEXT_MIN_WORDS", "80"))


class PDFDocumentProcessingError(RuntimeError):
    pass


def is_pdf_url(value: str | None) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    if parsed.scheme.lower() != "https":
        return False

    return bool(re.search(r"\.pdf(?:$|[?#])", parsed.path, re.IGNORECASE))


def resolve_bill_pdf_url(full_text_url: str | None = None, parliament_url: str | None = None) -> str | None:
    for candidate in (full_text_url, parliament_url):
        if is_pdf_url(candidate):
            return candidate
    return None


def _download_pdf(source_url: str, timeout: int = 60) -> Path:
    try:
        response = requests.get(
            source_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BungeMkononiBot/1.0)",
                "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PDFDocumentProcessingError(f"Unable to download PDF: {exc}") from exc

    if "pdf" not in (response.headers.get("content-type") or "").lower() and not response.content.startswith(b"%PDF"):
        raise PDFDocumentProcessingError("The source URL did not return a PDF document.")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        temp_file.write(response.content)
    finally:
        temp_file.close()

    return Path(temp_file.name)


def _run_command(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout)
    except FileNotFoundError as exc:
        raise PDFDocumentProcessingError(f"Required command not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise PDFDocumentProcessingError(f"Command timed out: {args[0]}") from exc


def _extract_pdf_page_count(pdf_path: Path) -> int:
    result = _run_command(["pdfinfo", str(pdf_path)])
    if result.returncode != 0:
        raise PDFDocumentProcessingError(result.stderr.strip() or "Unable to inspect PDF metadata.")

    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        return 0
    return int(match.group(1))


def _extract_pdf_text(pdf_path: Path) -> str:
    result = _run_command(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])
    if result.returncode != 0:
        raise PDFDocumentProcessingError(result.stderr.strip() or "Unable to extract text from PDF.")
    return result.stdout or ""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _count_words(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def _strip_page_noise(line: str) -> str:
    cleaned = _normalize_whitespace(line)
    if not cleaned:
        return ""
    if re.fullmatch(r"\d+", cleaned):
        return ""
    if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", cleaned, re.IGNORECASE):
        return ""
    return cleaned


def _looks_like_heading(line: str) -> bool:
    cleaned = _normalize_whitespace(line)
    if not cleaned or len(cleaned) > 140:
        return False

    word_count = len(cleaned.split())
    if word_count > 14:
        return False

    if cleaned.isupper() and any(ch.isalpha() for ch in cleaned):
        return True

    if re.match(r"^(PART|CHAPTER|SCHEDULE|ANNEX|SECTION)\b", cleaned, re.IGNORECASE):
        return True

    if re.match(r"^\d+(\.\d+)*\s+[A-Z]", cleaned):
        return True

    if cleaned.endswith(":") and word_count <= 8:
        return True

    return False


def _heading_level(line: str) -> int:
    cleaned = _normalize_whitespace(line)
    if re.match(r"^(PART|CHAPTER|SCHEDULE)\b", cleaned, re.IGNORECASE):
        return 1
    if cleaned.isupper():
        return 2
    return 3


def _looks_like_list_item(line: str) -> bool:
    cleaned = _normalize_whitespace(line)
    return bool(
        re.match(r"^(\(?\d+\)?[\.)]|[a-zA-Z][\.)]|[-•])\s+", cleaned)
    )


def _strip_list_marker(line: str) -> str:
    cleaned = _normalize_whitespace(line)
    cleaned = re.sub(r"^(\(?\d+\)?[\.)]|[a-zA-Z][\.)]|[-•])\s+", "", cleaned)
    return cleaned.strip()


def _structure_page_text(raw_page_text: str, page_number: int) -> dict[str, Any]:
    lines = [_strip_page_noise(line) for line in raw_page_text.splitlines()]
    lines = [line for line in lines if line]

    blocks: list[dict[str, Any]] = []
    paragraph_parts: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_parts:
            paragraph = _normalize_whitespace(" ".join(paragraph_parts))
            if paragraph:
                blocks.append({"type": "paragraph", "text": paragraph})
            paragraph_parts.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append({"type": "list", "items": list(list_items)})
            list_items.clear()

    for line in lines:
        if _looks_like_heading(line):
            flush_paragraph()
            flush_list()
            blocks.append({
                "type": "heading",
                "text": _normalize_whitespace(line),
                "level": _heading_level(line),
            })
            continue

        if _looks_like_list_item(line):
            flush_paragraph()
            list_items.append(_strip_list_marker(line))
            continue

        if list_items:
            flush_list()
        paragraph_parts.append(line)

    flush_paragraph()
    flush_list()

    return {
        "pageNumber": page_number,
        "blocks": blocks,
    }


def _structure_pages_from_text(extracted_text: str, page_count: int) -> list[dict[str, Any]]:
    raw_pages = extracted_text.split("\f") if extracted_text else []
    pages: list[dict[str, Any]] = []

    if not raw_pages:
        return pages

    for index, raw_page_text in enumerate(raw_pages, start=1):
        normalized_page_text = _normalize_whitespace(raw_page_text)
        if not normalized_page_text:
            continue
        pages.append(_structure_page_text(raw_page_text, index))

    if page_count and len(pages) < page_count and len(raw_pages) == 1:
        # Some tools collapse all pages into a single chunk. Preserve it as a single page rather than
        # pretending we have page-by-page structure.
        return [_structure_page_text(extracted_text, 1)]

    return pages


def _ocr_pdf_with_ocrmypdf(pdf_path: Path) -> str:
    if not shutil.which("ocrmypdf"):
        raise PDFDocumentProcessingError("OCRmyPDF is not installed.")

    with tempfile.TemporaryDirectory(prefix="bunge-pdf-ocrpdf-") as temp_dir:
        output_pdf = Path(temp_dir) / "ocr.pdf"
        result = _run_command(
            [
                "ocrmypdf",
                "--quiet",
                "--skip-text",
                "--force-ocr",
                str(pdf_path),
                str(output_pdf),
            ],
            timeout=600,
        )

        if result.returncode != 0 or not output_pdf.exists():
            raise PDFDocumentProcessingError(result.stderr.strip() or "OCRmyPDF failed to process the PDF.")

        return _extract_pdf_text(output_pdf)


def analyze_pdf_document(source_url: str, timeout: int = 60) -> dict[str, Any]:
    pdf_path: Path | None = None
    try:
        pdf_path = _download_pdf(source_url, timeout=timeout)
        page_count = _extract_pdf_page_count(pdf_path)
        extracted_text = _extract_pdf_text(pdf_path)
        normalized_text = _normalize_whitespace(extracted_text.replace("\f", " \f "))
        word_count = _count_words(normalized_text)

        if word_count >= PDF_TEXT_MIN_WORDS:
            return {
                "status": "ready",
                "method": "text",
                "sourceUrl": source_url,
                "text": normalized_text,
                "pages": _structure_pages_from_text(extracted_text, page_count),
                "pageCount": page_count,
                "wordCount": word_count,
                "error": "",
            }

        if shutil.which("ocrmypdf"):
            try:
                ocr_text = _ocr_pdf_with_ocrmypdf(pdf_path)
                ocr_normalized_text = _normalize_whitespace(ocr_text.replace("\f", " \f "))
                ocr_word_count = _count_words(ocr_normalized_text)
                if ocr_word_count > 0:
                    return {
                        "status": "ready",
                        "method": "ocr",
                        "sourceUrl": source_url,
                        "text": ocr_normalized_text,
                        "pages": _structure_pages_from_text(ocr_text, page_count),
                        "pageCount": page_count,
                        "wordCount": ocr_word_count,
                        "error": "",
                    }
                ocr_error = "OCRmyPDF returned no readable text."
            except PDFDocumentProcessingError as exc:
                ocr_error = str(exc)
        else:
            ocr_error = "OCRmyPDF is not installed."

        return {
            "status": "needs_ocr",
            "method": "",
            "sourceUrl": source_url,
            "text": normalized_text,
            "pages": _structure_pages_from_text(extracted_text, page_count),
            "pageCount": page_count,
            "wordCount": word_count,
            "error": ocr_error,
        }
    except PDFDocumentProcessingError as exc:
        return {
            "status": "failed",
            "method": "",
            "sourceUrl": source_url,
            "text": "",
            "pages": [],
            "pageCount": 0,
            "wordCount": 0,
            "error": str(exc),
        }
    finally:
        if pdf_path is not None:
            try:
                pdf_path.unlink(missing_ok=True)
            except OSError:
                pass
