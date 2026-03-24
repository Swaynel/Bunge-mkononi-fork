"""
Scraper helpers for the Kenyan Parliament bills page.

This module fetches the bills listing page, parses bill cards or table rows,
and upserts the results into the local Bill table.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import BillStatus
from .services import process_bill_document, update_bill_status

logger = logging.getLogger(__name__)

DEFAULT_PARLIAMENT_URL = "https://www.parliament.go.ke/the-national-assembly/house-business/bills"
DEFAULT_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; BungeMkononiBot/1.0; "
    "+https://github.com/ANNGLORIOUS/Bunge-mkononi)"
)

STAGE_MAP: dict[str, str] = {
    "first reading": "First Reading",
    "first": "First Reading",
    "committee": "Committee",
    "committee stage": "Committee",
    "second reading": "Second Reading",
    "second": "Second Reading",
    "third reading": "Third Reading",
    "third": "Third Reading",
    "assent": "Presidential Assent",
    "presidential assent": "Presidential Assent",
    "enacted": "Presidential Assent",
    "passed": "Third Reading",
    "withdrawn": "First Reading",
    "defeated": "First Reading",
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Finance": ["finance", "tax", "revenue", "budget", "fiscal", "excise", "levy", "duty", "banking", "insurance"],
    "Health": ["health", "medical", "hospital", "mental", "pharmacy", "nursing", "medicine"],
    "Education": ["education", "university", "college", "school", "curriculum", "student"],
    "Justice": [
        "justice",
        "court",
        "law",
        "crime",
        "penal",
        "constitution",
        "judiciary",
        "police",
        "security",
        "anti-corruption",
        "ethics",
        "land",
        "environment",
        "climate",
        "conservation",
    ],
}


def _normalise_stage(raw: str) -> str:
    key = raw.strip().lower()
    return STAGE_MAP.get(key, "First Reading")


def _guess_category(title: str, summary: str = "") -> str:
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "Justice"


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    match = re.search(r"\b(\d{4})\b", raw)
    if match:
        return date(int(match.group(1)), 1, 1)
    return None


def _slugify_id(title: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:60]
    return slug if slug else f"bill-{index}"


def _normalise_bill_title(raw: str) -> str:
    title = raw.replace("\xa0", " ").strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"\.pdf$", "", title, flags=re.IGNORECASE)
    title = title.rstrip(" -:|")
    return title.strip()


def _looks_like_bill_title(title: str) -> bool:
    lowered = title.lower()
    if lowered in {
        "bill tracker",
        "bill digest",
        "submit comments",
        "current page 1",
        "next page",
        "last page",
        "view archive",
        "bills",
        "acts",
        "home",
    }:
        return False

    return any(keyword in lowered for keyword in ("bill", "act", "amendment"))


def _parse_bill_links(html: str, base_url: str = DEFAULT_PARLIAMENT_URL) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    bills: list[dict] = []
    seen_titles: set[str] = set()

    for index, anchor in enumerate(soup.find_all("a", href=True), start=1):
        title = _normalise_bill_title(anchor.get_text(separator=" ", strip=True))
        if len(title) < 4 or not _looks_like_bill_title(title):
            continue

        dedupe_key = title.lower()
        if dedupe_key in seen_titles:
            continue
        seen_titles.add(dedupe_key)

        href = anchor["href"]
        bills.append(
            {
                "id": _slugify_id(title, index),
                "title": title,
                "sponsor": "Government",
                "status": BillStatus.FIRST_READING,
                "category": _guess_category(title),
                "date_introduced": date.today(),
                "parliament_url": urljoin(base_url, href),
                "summary": f"{title}.",
                "is_hot": "finance" in title.lower() or "amendment" in title.lower(),
            }
        )

    return bills


def _extract_pagination_urls(html: str, current_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []

    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(separator=" ", strip=True).split()).lower()
        href = urljoin(current_url, anchor["href"]).split("#", 1)[0]

        if href == current_url:
            continue

        is_page_link = (
            re.fullmatch(r"\d+", text) is not None
            or text.startswith("page ")
            or text.startswith("next")
            or text.startswith("previous")
            or "current page" in text
            or "next page" in text
            or "previous page" in text
            or "last page" in text
            or "page=" in anchor["href"]
        )

        if is_page_link and href not in urls:
            urls.append(href)

    return urls


def fetch_bills_page(url: str = DEFAULT_PARLIAMENT_URL, timeout: int = DEFAULT_TIMEOUT) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_bill_pages(
    url: str = DEFAULT_PARLIAMENT_URL,
    timeout: int = DEFAULT_TIMEOUT,
    max_pages: int = 25,
) -> tuple[list[tuple[str, str]], list[str]]:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    session = requests.Session()
    pages: list[tuple[str, str]] = []
    errors: list[str] = []
    queue = [url]
    seen: set[str] = set()

    while queue and len(seen) < max_pages:
        current_url = queue.pop(0).split("#", 1)[0]
        if current_url in seen:
            continue

        seen.add(current_url)

        try:
            response = session.get(current_url, headers=headers, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(f"Failed to fetch {current_url}: {exc}")
            continue

        html = response.text
        pages.append((current_url, html))

        for next_url in _extract_pagination_urls(html, current_url):
            if next_url not in seen and next_url not in queue:
                queue.append(next_url)

    return pages, errors


def parse_bills_html(html: str, base_url: str = DEFAULT_PARLIAMENT_URL) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    bills: list[dict] = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        header_row = rows[0] if rows else None
        if not header_row:
            continue

        headers_text = [cell.get_text(strip=True).lower() for cell in header_row.find_all(["th", "td"])]

        def col(name: str, fallback: int = -1) -> int:
            for i, header in enumerate(headers_text):
                if name in header:
                    return i
            return fallback

        idx_title = col("bill", col("title", 0))
        idx_sponsor = col("sponsor", col("member", col("introduc", 1)))
        idx_stage = col("stage", col("status", col("reading", 2)))
        idx_date = col("date", col("introduc", 3))

        for i, row in enumerate(rows[1:], start=1):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            def cell_text(idx: int) -> str:
                if 0 <= idx < len(cells):
                    return cells[idx].get_text(separator=" ", strip=True)
                return ""

            title = cell_text(idx_title)
            title = _normalise_bill_title(title)
            if not title or len(title) < 4 or not _looks_like_bill_title(title):
                continue

            sponsor = cell_text(idx_sponsor) or "Government"
            stage_raw = cell_text(idx_stage)
            date_raw = cell_text(idx_date)

            parliament_url = ""
            if 0 <= idx_title < len(cells):
                link = cells[idx_title].find("a", href=True)
                if link:
                    parliament_url = urljoin(base_url, link["href"])

            bill_id = _slugify_id(title, i)
            bills.append(
                {
                    "id": bill_id,
                    "title": title,
                    "sponsor": sponsor,
                    "status": _normalise_stage(stage_raw),
                    "category": _guess_category(title),
                    "date_introduced": _parse_date(date_raw) or date.today(),
                    "parliament_url": parliament_url or base_url,
                    "summary": f"{title} - introduced by {sponsor}.",
                    "is_hot": "finance" in title.lower() or "amendment" in title.lower(),
                }
            )

    if bills:
        return bills

    for i, item in enumerate(soup.select(".bill-item, .views-row, article, li.bill"), start=1):
        title_el = item.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        title = _normalise_bill_title(title)
        if len(title) < 4 or not _looks_like_bill_title(title):
            continue

        parliament_url = ""
        link = item.find("a", href=True)
        if link:
            parliament_url = urljoin(base_url, link["href"])

        text = item.get_text(separator=" ", strip=True)
        stage_raw = ""
        match = re.search(r"(first|second|third|committee|assent)\s*reading", text, re.I)
        if match:
            stage_raw = match.group(0)

        bill_id = _slugify_id(title, i)
        bills.append(
            {
                "id": bill_id,
                "title": title,
                "sponsor": "Government",
                "status": _normalise_stage(stage_raw),
                "category": _guess_category(title),
                "date_introduced": date.today(),
                "parliament_url": parliament_url or base_url,
                "summary": f"{title}.",
                "is_hot": False,
            }
        )

    if bills:
        return bills

    return _parse_bill_links(html, base_url=base_url)


def parse_bill_pages(pages: list[tuple[str, str]]) -> list[dict]:
    bills: list[dict] = []
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()

    for page_url, html in pages:
        for bill in parse_bills_html(html, base_url=page_url):
            bill_id = bill["id"]
            title_key = bill["title"].strip().lower()
            if bill_id in seen_ids or title_key in seen_titles:
                continue
            seen_ids.add(bill_id)
            seen_titles.add(title_key)
            bills.append(bill)

    return bills


def upsert_bills(bills: list[dict]) -> dict:
    from apps.legislative.models import Bill  # noqa: PLC0415

    created = 0
    updated = 0
    errors: list[str] = []
    processed_bills: list[dict] = []

    for data in bills:
        try:
            bill_id = data.pop("id")
            title = data.get("title", bill_id)
            sponsor = data.get("sponsor", "")
            previous_bill = Bill.objects.filter(pk=bill_id).only("status").first()
            previous_status = previous_bill.status if previous_bill else None
            bill, was_created = Bill.objects.update_or_create(id=bill_id, defaults=data)
            if was_created:
                created += 1
                action = "created"
            else:
                updated += 1
                action = "updated"
                if previous_status and previous_status != bill.status:
                    update_bill_status(bill, bill.status, previous_status=previous_status, actor="scrape")

            document_result = process_bill_document(bill)
            processed_bills.append(
                {
                    "bill_id": bill_id,
                    "title": title,
                    "action": action,
                    "sponsor": sponsor,
                    "document_status": document_result.get("status", ""),
                    "document_method": document_result.get("method", ""),
                }
            )
            if document_result.get("status") == "failed":
                document_error = str(document_result.get("error") or "").strip()
                if document_error:
                    errors.append(f"Document processing failed for '{title}': {document_error}")
        except Exception as exc:  # noqa: BLE001
            message = f"Error upserting bill '{data.get('title', '?')}': {exc}"
            logger.error(message)
            errors.append(message)

    return {"created": created, "updated": updated, "errors": errors, "processed_bills": processed_bills}


def scrape_parliament_bills(
    url: str = DEFAULT_PARLIAMENT_URL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    logger.info("Starting parliament bills scrape from %s", url)

    pages, fetch_errors = fetch_bill_pages(url, timeout=timeout)
    if not pages:
        logger.error("Failed to fetch any bill pages from %s", url)
        return {
            "url": url,
            "bills_found": 0,
            "created": 0,
            "updated": 0,
            "errors": fetch_errors or [f"Failed to fetch {url}"],
            "processed_bills": [],
            "pages_fetched": 0,
        }

    bills = parse_bill_pages(pages)
    logger.info("Parsed %d bills from %d page(s)", len(bills), len(pages))

    summary = upsert_bills(bills)
    summary["url"] = url
    summary["bills_found"] = len(bills)
    summary["pages_fetched"] = len(pages)
    summary["errors"] = fetch_errors + summary["errors"]

    logger.info(
        "Scrape complete: %d found, %d created, %d updated, %d errors",
        summary["bills_found"],
        summary["created"],
        summary["updated"],
        len(summary["errors"]),
    )
    return summary
