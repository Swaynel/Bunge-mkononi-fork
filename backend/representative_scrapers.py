"""
backend/apps/legislative/representative_scrapers.py

Scrapes Kenyan MPs, Senators, and their voting records from:
  - https://www.parliament.go.ke/the-national-assembly/mps      (MPs)
  - https://www.parliament.go.ke/the-senate/senators            (Senators)
  - Hansard division lists for voting records

Responsibilities:
  - Fetch member listing pages (with pagination)
  - Parse each member card: name, role, constituency/county, party
  - Scrape division/voting records and link them to Bills
  - Upsert into Representative and RepresentativeVote models
  - Return structured summary dicts

Entry points:
  scrape_representatives(url, role, timeout) -> dict
  scrape_representative_votes(bill_id, url, timeout) -> dict
  scrape_all(timeout) -> dict
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 5
USER_AGENT = (
    "Mozilla/5.0 (compatible; BungeMkononiBot/1.0; "
    "+https://github.com/ANNGLORIOUS/Bunge-mkononi)"
)

MP_URL = "https://www.parliament.go.ke/the-national-assembly/mps"
MP_URL_ALTERNATES = [
    MP_URL,
    "https://www.parliament.go.ke/index.php/the-national-assembly/mps",
]
SENATOR_URL = "https://www.parliament.go.ke/the-senate/senators"

# Hansard division records (voting) — National Assembly
HANSARD_VOTES_URL = "https://www.parliament.go.ke/the-national-assembly/house-business/hansard"

# Kenya counties for constituency → county mapping
KENYA_COUNTIES: dict[str, str] = {
    # Nairobi
    "westlands": "Nairobi", "dagoretti north": "Nairobi", "dagoretti south": "Nairobi",
    "langata": "Nairobi", "kibra": "Nairobi", "roysambu": "Nairobi", "kasarani": "Nairobi",
    "ruaraka": "Nairobi", "embakasi south": "Nairobi", "embakasi north": "Nairobi",
    "embakasi central": "Nairobi", "embakasi east": "Nairobi", "embakasi west": "Nairobi",
    "makadara": "Nairobi", "kamukunji": "Nairobi", "starehe": "Nairobi", "mathare": "Nairobi",
    # Mombasa
    "changamwe": "Mombasa", "jomvu": "Mombasa", "kisauni": "Mombasa",
    "nyali": "Mombasa", "likoni": "Mombasa", "mvita": "Mombasa",
    # Kwale
    "msambweni": "Kwale", "lungalunga": "Kwale", "matuga": "Kwale", "kinango": "Kwale",
    # Kilifi
    "kilifi north": "Kilifi", "kilifi south": "Kilifi", "kaloleni": "Kilifi",
    "rabai": "Kilifi", "ganze": "Kilifi", "malindi": "Kilifi", "magarini": "Kilifi",
    # Tana River
    "garsen": "Tana River", "galole": "Tana River", "bura": "Tana River",
    # Lamu
    "lamu east": "Lamu", "lamu west": "Lamu",
    # Taita-Taveta
    "taveta": "Taita-Taveta", "wundanyi": "Taita-Taveta",
    "mwatate": "Taita-Taveta", "voi": "Taita-Taveta",
    # Garissa
    "garissa township": "Garissa", "balambala": "Garissa", "lagdera": "Garissa",
    "dadaab": "Garissa", "fafi": "Garissa", "ijara": "Garissa",
    # Wajir
    "wajir north": "Wajir", "wajir east": "Wajir", "tarbaj": "Wajir",
    "wajir west": "Wajir", "eldas": "Wajir", "wajir south": "Wajir",
    # Mandera
    "mandera north": "Mandera", "mandera west": "Mandera", "mandera south": "Mandera",
    "banissa": "Mandera", "mandera east": "Mandera", "lafey": "Mandera",
    # Marsabit
    "moyale": "Marsabit", "north horr": "Marsabit", "saku": "Marsabit", "laisamis": "Marsabit",
    # Isiolo
    "isiolo north": "Isiolo", "isiolo south": "Isiolo",
    # Meru
    "igembe south": "Meru", "igembe central": "Meru", "igembe north": "Meru",
    "tigania west": "Meru", "tigania east": "Meru", "north imenti": "Meru",
    "buuri": "Meru", "central imenti": "Meru", "south imenti": "Meru",
    # Tharaka-Nithi
    "maara": "Tharaka-Nithi", "chuka": "Tharaka-Nithi", "tharaka": "Tharaka-Nithi",
    # Embu
    "manyatta": "Embu", "runyenjes": "Embu", "mbeere south": "Embu", "mbeere north": "Embu",
    # Kitui
    "mwingi north": "Kitui", "mwingi west": "Kitui", "mwingi central": "Kitui",
    "kitui west": "Kitui", "kitui rural": "Kitui", "kitui central": "Kitui",
    "kitui east": "Kitui", "kitui south": "Kitui",
    # Machakos
    "masinga": "Machakos", "yatta": "Machakos", "kangundo": "Machakos",
    "matungulu": "Machakos", "kathiani": "Machakos", "mavoko": "Machakos",
    "machakos town": "Machakos", "mwala": "Machakos",
    # Makueni
    "mbooni": "Makueni", "kilome": "Makueni", "kaiti": "Makueni",
    "makueni": "Makueni", "kibwezi west": "Makueni", "kibwezi east": "Makueni",
    # Nyandarua
    "kinangop": "Nyandarua", "kipipiri": "Nyandarua", "ol kalou": "Nyandarua",
    "ol jorok": "Nyandarua", "ndaragwa": "Nyandarua",
    # Nyeri
    "tetu": "Nyeri", "kieni": "Nyeri", "mathira": "Nyeri", "othaya": "Nyeri",
    "mukurwe-ini": "Nyeri", "nyeri town": "Nyeri",
    # Kirinyaga
    "mwea": "Kirinyaga", "gichugu": "Kirinyaga", "ndia": "Kirinyaga", "kirinyaga central": "Kirinyaga",
    # Murang'a
    "kangema": "Murang'a", "mathioya": "Murang'a", "kiharu": "Murang'a",
    "kigumo": "Murang'a", "maragwa": "Murang'a", "kandara": "Murang'a", "gatanga": "Murang'a",
    # Kiambu
    "gatundu south": "Kiambu", "gatundu north": "Kiambu", "juja": "Kiambu",
    "thika town": "Kiambu", "ruiru": "Kiambu", "githunguri": "Kiambu",
    "kiambu": "Kiambu", "kiambaa": "Kiambu", "kabete": "Kiambu",
    "kikuyu": "Kiambu", "limuru": "Kiambu", "lari": "Kiambu",
    # Turkana
    "turkana north": "Turkana", "turkana west": "Turkana", "turkana central": "Turkana",
    "loima": "Turkana", "turkana south": "Turkana", "turkana east": "Turkana",
    # West Pokot
    "kapenguria": "West Pokot", "sigor": "West Pokot", "kacheliba": "West Pokot", "pokot south": "West Pokot",
    # Samburu
    "samburu west": "Samburu", "samburu north": "Samburu", "samburu east": "Samburu",
    # Trans-Nzoia
    "kwanza": "Trans-Nzoia", "endebess": "Trans-Nzoia", "saboti": "Trans-Nzoia",
    "kiminini": "Trans-Nzoia", "cherangany": "Trans-Nzoia",
    # Uasin Gishu
    "soy": "Uasin Gishu", "turbo": "Uasin Gishu", "moiben": "Uasin Gishu",
    "ainabkoi": "Uasin Gishu", "kapseret": "Uasin Gishu", "kesses": "Uasin Gishu",
    # Elgeyo-Marakwet
    "marakwet east": "Elgeyo-Marakwet", "marakwet west": "Elgeyo-Marakwet",
    "keiyo north": "Elgeyo-Marakwet", "keiyo south": "Elgeyo-Marakwet",
    # Nandi
    "tinderet": "Nandi", "aldai": "Nandi", "nandi hills": "Nandi",
    "chesumei": "Nandi", "emgwen": "Nandi", "mosop": "Nandi",
    # Baringo
    "tiaty": "Baringo", "baringo north": "Baringo", "baringo central": "Baringo",
    "baringo south": "Baringo", "eldama ravine": "Baringo", "mogotio": "Baringo",
    # Laikipia
    "laikipia west": "Laikipia", "laikipia east": "Laikipia", "laikipia north": "Laikipia",
    # Nakuru
    "molo": "Nakuru", "njoro": "Nakuru", "naivasha": "Nakuru", "gilgil": "Nakuru",
    "kuresoi south": "Nakuru", "kuresoi north": "Nakuru", "subukia": "Nakuru",
    "rongai": "Nakuru", "bahati": "Nakuru", "nakuru town west": "Nakuru", "nakuru town east": "Nakuru",
    # Narok
    "kilgoris": "Narok", "emurua dikirr": "Narok", "narok north": "Narok",
    "narok east": "Narok", "narok south": "Narok", "narok west": "Narok",
    # Kajiado
    "kajiado north": "Kajiado", "kajiado central": "Kajiado", "kajiado east": "Kajiado",
    "kajiado west": "Kajiado", "kajiado south": "Kajiado",
    # Kericho
    "kipkelion east": "Kericho", "kipkelion west": "Kericho", "ainamoi": "Kericho",
    "bureti": "Kericho", "belgut": "Kericho", "sigowet": "Kericho",
    # Bomet
    "sotik": "Bomet", "chepalungu": "Bomet", "bomet east": "Bomet",
    "bomet central": "Bomet", "konoin": "Bomet",
    # Kakamega
    "lugari": "Kakamega", "likuyani": "Kakamega", "malava": "Kakamega",
    "lurambi": "Kakamega", "navakholo": "Kakamega", "mumias west": "Kakamega",
    "mumias east": "Kakamega", "matungu": "Kakamega", "butere": "Kakamega",
    "khwisero": "Kakamega", "shinyalu": "Kakamega", "ikolomani": "Kakamega",
    # Vihiga
    "vihiga": "Vihiga", "sabatia": "Vihiga", "hamisi": "Vihiga",
    "luanda": "Vihiga", "emuhaya": "Vihiga",
    # Bungoma
    "mount elgon": "Bungoma", "sirisia": "Bungoma", "kabuchai": "Bungoma",
    "bumula": "Bungoma", "kanduyi": "Bungoma", "webuye east": "Bungoma",
    "webuye west": "Bungoma", "kimilili": "Bungoma", "tongaren": "Bungoma",
    # Busia
    "teso north": "Busia", "teso south": "Busia", "nambale": "Busia",
    "matayos": "Busia", "butula": "Busia", "funyula": "Busia", "budalangi": "Busia",
    # Siaya
    "gem": "Siaya", "ugenya": "Siaya", "ugunja": "Siaya",
    "alego usonga": "Siaya", "bondo": "Siaya", "rarieda": "Siaya",
    # Kisumu
    "kisumu east": "Kisumu", "kisumu west": "Kisumu", "kisumu central": "Kisumu",
    "seme": "Kisumu", "nyando": "Kisumu", "muhoroni": "Kisumu", "nyakach": "Kisumu",
    # Homa Bay
    "kasipul": "Homa Bay", "kabondo kasipul": "Homa Bay", "karachuonyo": "Homa Bay",
    "rangwe": "Homa Bay", "homa bay town": "Homa Bay", "ndhiwa": "Homa Bay",
    "mbita": "Homa Bay", "suba north": "Homa Bay", "suba south": "Homa Bay",
    # Migori
    "rongo": "Migori", "awendo": "Migori", "suna east": "Migori",
    "suna west": "Migori", "uriri": "Migori", "nyatike": "Migori",
    "kuria west": "Migori", "kuria east": "Migori",
    # Kisii
    "bonchari": "Kisii", "south mugirango": "Kisii", "bomachoge borabu": "Kisii",
    "bobasi": "Kisii", "bomachoge chache": "Kisii", "nyaribari masaba": "Kisii",
    "nyaribari chache": "Kisii", "kitutu chache north": "Kisii", "kitutu chache south": "Kisii",
    # Nyamira
    "kitutu masaba": "Nyamira", "west mugirango": "Nyamira", "north mugirango": "Nyamira",
    "borabu": "Nyamira",
}

VOTE_NORMALISATION: dict[str, str] = {
    "aye": "Yes", "yes": "Yes", "yea": "Yes", "for": "Yes", "y": "Yes",
    "no": "No", "nay": "No", "against": "No", "n": "No",
    "abstain": "Abstain", "abstained": "Abstain", "absent": "Abstain",
    "not voting": "Abstain", "paired": "Abstain",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    r = requests.get(
        url,
        headers=headers,
        timeout=(min(DEFAULT_CONNECT_TIMEOUT, timeout), timeout),
    )
    r.raise_for_status()
    return r.text


def _slugify(text: str, max_len: int = 64) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len] if slug else "unknown"


def _county_for_constituency(constituency: str) -> str:
    return KENYA_COUNTIES.get(constituency.strip().lower(), "")


KENYA_COUNTY_NAMES: set[str] = {county.lower() for county in KENYA_COUNTIES.values()}


def _looks_like_location_metadata(text: str) -> bool:
    candidate = _clean(text)
    if not candidate:
        return False

    normalized = candidate.lower()
    return (
        normalized in KENYA_COUNTY_NAMES
        or _county_for_constituency(candidate) != ""
        or any(keyword in normalized for keyword in ("county", "constituency", "ward"))
    )


def _normalise_vote(raw: str) -> str:
    return VOTE_NORMALISATION.get(raw.strip().lower(), "Abstain")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _looks_like_generic_member_link(text: str) -> bool:
    normalized = _clean(text).lower()
    if not normalized:
        return True
    return normalized in {
        "more",
        "more info",
        "more...",
        "more info...",
        "profile",
        "view profile",
        "read more",
        "image",
    }


def _meaningful_link_hint(anchor) -> str:
    for attribute in ("title", "aria-label", "data-title"):
        value = _clean(str(anchor.get(attribute) or ""))
        if value and not _looks_like_generic_member_link(value):
            return value

    text = _clean(anchor.get_text(separator=" ", strip=True))
    if text and not _looks_like_generic_member_link(text):
        return text

    return ""


def _leading_row_text(item) -> str:
    parts: list[str] = []
    for child in item.children:
        if getattr(child, "name", None) in {"a", "img", "figure", "svg"}:
            break
        if isinstance(child, str):
            text = _clean(child)
        else:
            text = _clean(getattr(child, "get_text", lambda **_: "")(separator=" ", strip=True))
        if text:
            parts.append(text)

    return _clean(" ".join(parts))


def _candidate_name(value: str) -> str:
    cleaned = _clean(value)
    if not cleaned:
        return ""

    cleaned = re.sub(r"^(more\s+info(?:\.\.\.)?|more\.{0,3})\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(profile|view profile|read more)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split(" | ", 1)[0]
    cleaned = cleaned.split(" - ", 1)[0]
    cleaned = cleaned.split(" — ", 1)[0]
    cleaned = cleaned.split(" – ", 1)[0]

    comma_parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(comma_parts) >= 2:
        tail = comma_parts[-1]
        if tail.isupper() or tail.lower() in {"elected", "nominated"} or _looks_like_location_metadata(tail):
            cleaned = comma_parts[0]

    cleaned = cleaned.split(":", 1)[0].strip()

    if len(cleaned.split()) >= 2 and any(ch.isalpha() for ch in cleaned):
        return cleaned
    return ""


def _extract_member_name_from_item(item) -> str:
    for anchor in item.find_all("a", href=True):
        hint = _candidate_name(_meaningful_link_hint(anchor))
        if hint:
            return hint

    leading_text = _candidate_name(_leading_row_text(item))
    if leading_text:
        return leading_text

    full_text = _candidate_name(_clean(item.get_text(separator=" ", strip=True)))
    if full_text:
        return full_text

    return ""


def _extract_member_profile_url(item, base_url: str) -> str:
    for anchor in item.find_all("a", href=True):
        if _meaningful_link_hint(anchor):
            return urljoin(base_url, anchor["href"])
    return ""


def _extract_party_from_text(text: str) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""

    status_match = re.search(r"\b(Elected|Nominated)\b", cleaned, re.IGNORECASE)
    if status_match:
        cleaned = cleaned[: status_match.start()].strip()

    tokens = cleaned.split()
    if len(tokens) < 2:
        return ""

    tail = tokens[-1]
    if tail.startswith("(") or tail.isupper() or re.fullmatch(r"[A-Z][A-Z&'()\- ]{1,}", tail):
        return tail.strip(",")

    if len(tokens) >= 2:
        last_two = " ".join(tokens[-2:])
        if last_two.startswith("(") or re.fullmatch(r"[A-Z][A-Z&'()\- ]{1,}", last_two):
            return last_two.strip(",")

    return ""


def _extract_constituency_from_text(text: str) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""

    match = re.search(r"\b(Nominated|Elected)\b", cleaned, re.IGNORECASE)
    if match:
        cleaned = cleaned[: match.start()].strip()

    pieces = [piece for piece in re.split(r"\s{2,}|[|]", cleaned) if piece.strip()]
    if len(pieces) >= 2:
        candidate = _clean(pieces[-2])
        if candidate and _looks_like_location_metadata(candidate):
            return candidate

    comma_pieces = [piece for piece in re.split(r",", cleaned) if piece.strip()]
    if len(comma_pieces) >= 2:
        candidate = _clean(comma_pieces[-2] if len(comma_pieces) >= 3 else comma_pieces[-1])
        if candidate and _looks_like_location_metadata(candidate):
            return candidate

    return ""


def _extract_pagination_urls(html: str, current_url: str, max_pages: int = 20) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(separator=" ", strip=True).split()).lower()
        href = urljoin(current_url, a["href"]).split("#")[0]
        if href == current_url or href in urls:
            continue
        is_page = (
            re.fullmatch(r"\d+", text) is not None
            or text.startswith("next")
            or "page=" in a["href"]
            or "page-" in href
        )
        if is_page and len(urls) < max_pages:
            urls.append(href)
    return urls


# ---------------------------------------------------------------------------
# Member page parsers
# ---------------------------------------------------------------------------

def _parse_member_cards(html: str, base_url: str, role: str) -> list[dict]:
    """
    Parse parliament member cards/table rows.
    Returns a list of representative dicts.
    """
    soup = BeautifulSoup(html, "lxml")
    members: list[dict] = []
    seen: set[str] = set()

    # ── Strategy 1: table rows (most parliament pages) ───────────────────
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        header_cells = rows[0].find_all(["th", "td"])
        headers = [c.get_text(strip=True).lower() for c in header_cells]

        def col(name: str, fallback: int = -1) -> int:
            for i, h in enumerate(headers):
                if name in h:
                    return i
            return fallback

        i_name = col("name", col("member", 0))
        i_const = col("constituency", col("ward", col("county", 1)))
        i_party = col("party", col("coalition", 2))
        i_county = col("county", 3)

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            def cell(idx: int) -> str:
                if 0 <= idx < len(cells):
                    return _clean(cells[idx].get_text(separator=" ", strip=True))
                return ""

            name = cell(i_name)
            if not name or len(name) < 3:
                continue

            constituency = cell(i_const)
            party = cell(i_party) or "Independent"
            county = cell(i_county) or _county_for_constituency(constituency)

            # Grab profile link if any
            image_url = ""
            profile_url = ""
            link = cells[i_name].find("a", href=True) if 0 <= i_name < len(cells) else None
            if link:
                profile_url = urljoin(base_url, link["href"])
            img = row.find("img", src=True)
            if img:
                image_url = urljoin(base_url, img["src"])

            rep_id = _slugify(name)
            if rep_id in seen:
                continue
            seen.add(rep_id)

            members.append({
                "id": rep_id,
                "name": name,
                "role": role,
                "constituency": constituency,
                "county": county,
                "party": party,
                "image_url": image_url,
            })

    if members:
        return members

    # ── Strategy 2: member cards / profile divs ───────────────────────────
    selectors = [
        ".member-profile", ".member-card", ".mp-card",
        ".views-row", "article.member", ".field-content",
    ]
    for sel in selectors:
        items = soup.select(sel)
        if not items:
            continue
        for i, item in enumerate(items, start=1):
            profile_url = _extract_member_profile_url(item, base_url)
            title_hints = [
                _meaningful_link_hint(anchor)
                for anchor in item.find_all("a", href=True)
            ]
            title_hints = [hint for hint in title_hints if hint]

            name = _extract_member_name_from_item(item)
            if len(name) < 3:
                continue

            text = _clean(item.get_text(separator=" ", strip=True))

            constituency = ""
            m = re.search(
                r"(?:county|constituency|ward)[:\s]+([A-Za-z0-9\s'&().\-\/]+?)(?:\s+(?:party|status|email|phone|tel)\b|$)",
                text,
                re.IGNORECASE,
            )
            if m:
                constituency = _clean(m.group(1))

            if not constituency:
                for hint in title_hints:
                    hint_constituency = _extract_constituency_from_text(hint)
                    if hint_constituency:
                        constituency = hint_constituency
                        break

            party = ""
            m = re.search(r"(?:party|coalition)[:\s]+([A-Za-z0-9\s'&().\-\/]+)", text, re.IGNORECASE)
            if m:
                party = _clean(m.group(1))

            if not party:
                party = _extract_party_from_text(text)

            if not party:
                for hint in title_hints:
                    hint_party = _extract_party_from_text(hint)
                    if hint_party:
                        party = hint_party
                        break

            county = _county_for_constituency(constituency)
            image_url = ""
            img = item.find("img", src=True)
            if img:
                image_url = urljoin(base_url, img["src"])

            rep_id = _slugify(profile_url or name)
            if rep_id in seen:
                continue
            seen.add(rep_id)

            members.append({
                "id": rep_id,
                "name": name,
                "role": role,
                "constituency": constituency,
                "county": county,
                "party": party or "Independent",
                "image_url": image_url,
            })
        if members:
            break

    # ── Strategy 3: anchor link fallback ─────────────────────────────────
    if not members:
        for i, a in enumerate(soup.find_all("a", href=True), start=1):
            text = _meaningful_link_hint(a)
            if not text:
                continue

            name = _candidate_name(text)
            if not name:
                continue

            # Skip navigation / UI links
            if any(kw in name.lower() for kw in ["home", "contact", "search", "menu", "next", "page"]):
                continue

            parent = a.find_parent(class_=re.compile(r"views-row|member|profile", re.IGNORECASE))
            row_text = _clean(parent.get_text(separator=" ", strip=True)) if parent else _clean(a.get_text(separator=" ", strip=True))
            constituency = _extract_constituency_from_text(row_text) or _extract_constituency_from_text(text)
            party = _extract_party_from_text(row_text) or _extract_party_from_text(text)
            county = _county_for_constituency(constituency)

            rep_id = _slugify(urljoin(base_url, a["href"]))
            if rep_id in seen:
                continue
            seen.add(rep_id)
            members.append({
                "id": rep_id,
                "name": name,
                "role": role,
                "constituency": constituency,
                "county": county,
                "party": party or "Independent",
                "image_url": "",
            })

    return members


# ---------------------------------------------------------------------------
# Vote page parsers
# ---------------------------------------------------------------------------

def _parse_division_votes(html: str, base_url: str) -> list[dict]:
    """
    Parse a Hansard division page for voting records.
    Returns list of {name, vote} dicts.
    """
    soup = BeautifulSoup(html, "lxml")
    votes: list[dict] = []

    # ── Strategy 1: table with member name + vote columns ────────────────
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        headers = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]

        def col(name: str, fallback: int = -1) -> int:
            for i, h in enumerate(headers):
                if name in h:
                    return i
            return fallback

        i_name = col("member", col("name", col("mp", 0)))
        i_vote = col("vote", col("division", col("decision", 1)))

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            name = _clean(cells[i_name].get_text(separator=" ", strip=True)) if 0 <= i_name < len(cells) else ""
            vote_raw = _clean(cells[i_vote].get_text(separator=" ", strip=True)) if 0 <= i_vote < len(cells) else ""
            if name and vote_raw:
                votes.append({"name": name, "vote": _normalise_vote(vote_raw)})

    if votes:
        return votes

    # ── Strategy 2: "AYES"/"NOES" sections in Hansard plain text ─────────
    text = soup.get_text(separator="\n")
    current_vote: Optional[str] = None

    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()

        if "AYES" in upper and len(stripped) < 30:
            current_vote = "Yes"
            continue
        if "NOES" in upper and len(stripped) < 30:
            current_vote = "No"
            continue
        if "ABSTAIN" in upper and len(stripped) < 30:
            current_vote = "Abstain"
            continue

        if current_vote and stripped:
            # Lines like "Hon. Jane Doe (Westlands, UDA)"
            name_match = re.match(
                r"(?:Hon\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
                stripped,
            )
            if name_match:
                votes.append({"name": name_match.group(1).strip(), "vote": current_vote})

    return votes


# ---------------------------------------------------------------------------
# Fetch helpers (paginated)
# ---------------------------------------------------------------------------

ProgressCallback = Optional[Callable[[str], None]]


def _fetch_all_pages(
    start_url: str,
    timeout: int,
    progress: ProgressCallback = None,
) -> tuple[list[tuple[str, str]], list[str]]:
    pages: list[tuple[str, str]] = []
    errors: list[str] = []
    seen: set[str] = {start_url}
    queue: list[str] = [start_url]

    while queue:
        url = queue.pop(0)
        try:
            if progress:
                progress(url)
            html = _get(url, timeout=timeout)
            pages.append((url, html))
            for next_url in _extract_pagination_urls(html, url):
                if next_url not in seen:
                    seen.add(next_url)
                    queue.append(next_url)
        except requests.RequestException as exc:
            errors.append(f"Failed to fetch {url}: {exc}")

    return pages, errors


def _candidate_member_urls(role: str, url: str = "") -> list[str]:
    if url and role == "MP" and url in {MP_URL, *MP_URL_ALTERNATES}:
        return [url, *[candidate for candidate in MP_URL_ALTERNATES if candidate != url]]
    if url:
        return [url]
    if role == "MP":
        return list(MP_URL_ALTERNATES)
    if role == "Senator":
        return [SENATOR_URL]
    return [MP_URL]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def _upsert_representatives(members: list[dict]) -> dict:
    from apps.legislative.models import Representative  # noqa: PLC0415

    created = updated = 0
    errors: list[str] = []
    processed: list[dict] = []

    for data in members:
        try:
            rep_id = data.pop("id")
            _, was_created = Representative.objects.update_or_create(
                id=rep_id, defaults=data
            )
            action = "created" if was_created else "updated"
            if was_created:
                created += 1
            else:
                updated += 1
            processed.append({"id": rep_id, "name": data.get("name", rep_id), "action": action})
        except Exception as exc:  # noqa: BLE001
            msg = f"Error upserting representative '{data.get('name', '?')}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {"created": created, "updated": updated, "errors": errors, "processed": processed}


def _upsert_votes(votes: list[dict], bill_id: str) -> dict:
    """
    Match scraped vote records to existing Representatives by name and
    upsert RepresentativeVote rows.
    """
    from apps.legislative.models import Bill, Representative, RepresentativeVote  # noqa: PLC0415

    bill = Bill.objects.filter(pk=bill_id).first()
    if not bill:
        return {
            "created": 0, "updated": 0,
            "errors": [f"Bill '{bill_id}' not found in database."],
            "processed": [],
        }

    all_reps = {rep.name.lower(): rep for rep in Representative.objects.all()}

    created = updated = unmatched = 0
    errors: list[str] = []
    processed: list[dict] = []

    for vote_data in votes:
        name = vote_data.get("name", "").strip()
        vote_choice = vote_data.get("vote", "Abstain")

        # Match by name (exact, then partial)
        rep = all_reps.get(name.lower())
        if not rep:
            # Try matching any rep whose name contains the scraped name
            for key, candidate in all_reps.items():
                if name.lower() in key or key in name.lower():
                    rep = candidate
                    break

        if not rep:
            unmatched += 1
            errors.append(f"No representative found matching '{name}'")
            continue

        try:
            _, was_created = RepresentativeVote.objects.update_or_create(
                representative=rep,
                bill=bill,
                defaults={"vote": vote_choice},
            )
            action = "created" if was_created else "updated"
            if was_created:
                created += 1
            else:
                updated += 1
            processed.append({
                "representative": rep.name,
                "bill": bill_id,
                "vote": vote_choice,
                "action": action,
            })
        except Exception as exc:  # noqa: BLE001
            msg = f"Error upserting vote for '{name}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {
        "created": created,
        "updated": updated,
        "unmatched": unmatched,
        "errors": errors,
        "processed": processed,
    }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def scrape_representatives(
    url: str = MP_URL,
    role: str = "MP",
    timeout: int = DEFAULT_TIMEOUT,
    progress: ProgressCallback = None,
) -> dict:
    """
    Scrape parliament member listing and upsert into Representative table.

    Args:
        url:     Parliament members page URL.
        role:    'MP' | 'Senator' | 'MCA'
        timeout: HTTP timeout in seconds.

    Returns:
        {url, role, members_found, pages_fetched, created, updated, errors, processed}
    """
    logger.info("Scraping %s members from %s", role, url)

    candidate_urls = _candidate_member_urls(role, url)

    pages: list[tuple[str, str]] = []
    fetch_errors: list[str] = []
    for candidate_url in candidate_urls:
        candidate_pages, candidate_errors = _fetch_all_pages(
            candidate_url,
            timeout=timeout,
            progress=progress,
        )
        fetch_errors.extend(candidate_errors)
        if candidate_pages:
            pages = candidate_pages
            url = candidate_url
            break

    if not pages:
        return {
            "url": url, "role": role, "members_found": 0,
            "pages_fetched": 0, "created": 0, "updated": 0,
            "errors": fetch_errors or [f"Failed to fetch {url}"],
            "processed": [],
        }

    all_members: list[dict] = []
    seen_ids: set[str] = set()
    for page_url, html in pages:
        for member in _parse_member_cards(html, base_url=page_url, role=role):
            if member["id"] not in seen_ids:
                seen_ids.add(member["id"])
                all_members.append(member)

    logger.info("Parsed %d %s members from %d page(s)", len(all_members), role, len(pages))

    summary = _upsert_representatives(all_members)
    summary["url"] = url
    summary["role"] = role
    summary["members_found"] = len(all_members)
    summary["pages_fetched"] = len(pages)
    summary["errors"] = fetch_errors + summary["errors"]
    return summary


def scrape_representative_votes(
    bill_id: str,
    url: str = HANSARD_VOTES_URL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    Scrape division/voting records for a specific bill from the Hansard page
    and upsert into RepresentativeVote.

    Args:
        bill_id: The Bill.id to associate votes with.
        url:     URL of the Hansard division record page.
        timeout: HTTP timeout.

    Returns:
        {url, bill_id, votes_found, created, updated, unmatched, errors, processed}
    """
    logger.info("Scraping votes for bill '%s' from %s", bill_id, url)

    try:
        html = _get(url, timeout=timeout)
    except requests.RequestException as exc:
        return {
            "url": url, "bill_id": bill_id, "votes_found": 0,
            "created": 0, "updated": 0, "unmatched": 0,
            "errors": [f"Failed to fetch {url}: {exc}"], "processed": [],
        }

    raw_votes = _parse_division_votes(html, base_url=url)
    logger.info("Parsed %d vote records for bill '%s'", len(raw_votes), bill_id)

    summary = _upsert_votes(raw_votes, bill_id=bill_id)
    summary["url"] = url
    summary["bill_id"] = bill_id
    summary["votes_found"] = len(raw_votes)
    return summary


def scrape_all(timeout: int = DEFAULT_TIMEOUT, progress: ProgressCallback = None) -> dict:
    """
    Convenience wrapper: scrape both MPs and Senators.

    Returns a combined summary.
    """
    mp_summary = scrape_representatives(url=MP_URL, role="MP", timeout=timeout, progress=progress)
    senator_summary = scrape_representatives(
        url=SENATOR_URL,
        role="Senator",
        timeout=timeout,
        progress=progress,
    )

    return {
        "mp": mp_summary,
        "senator": senator_summary,
        "total_members_found": mp_summary["members_found"] + senator_summary["members_found"],
        "total_created": mp_summary["created"] + senator_summary["created"],
        "total_updated": mp_summary["updated"] + senator_summary["updated"],
        "total_errors": mp_summary["errors"] + senator_summary["errors"],
    }
