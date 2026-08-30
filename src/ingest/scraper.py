import json
import re
import time

import requests
from bs4 import BeautifulSoup

from src.logger import get_logger

log = get_logger("rbi_govern.scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

KYC_TERMS = [
    "kyc",
    "aml",
    "anti-money",
    "know your customer",
    "prevention of money",
    "customer due diligence",
    "video-based",
    "vcip",
]

DATE_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}$"
)

# KYC Master Directions were issued in 2016; go back to 2015 to catch anything earlier
NOTIFICATIONS_YEARS = [str(y) for y in range(2015, 2027)]
MASTER_DIR_YEARS = [str(y) for y in range(2015, 2027)]


def _is_kyc_relevant(title: str, category: str) -> bool:
    combined = (title + " " + category).lower()
    return any(term in combined for term in KYC_TERMS)


def _extract_viewstate(soup: BeautifulSoup) -> dict:
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        tag = soup.find("input", {"name": name})
        if tag:
            fields[name] = tag.get("value", "")
    if not fields:
        log.warning("No ViewState fields found in page — POST may fail")
    return fields


def _parse_page(html: str, source_page: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.find_all("tr")

    results = []
    current_category = ""
    current_date = ""

    for row in rows:
        header_td = row.find("td", class_="tableheader")
        if header_td:
            text = header_td.get_text(strip=True)
            if DATE_RE.match(text):
                current_date = text
            else:
                current_category = text
            continue

        link2 = row.find("a", class_="link2")
        if not link2:
            continue

        title = link2.get_text(strip=True)

        pdf_link = row.find("a", href=re.compile(r"\.PDF$", re.IGNORECASE))
        if not pdf_link:
            log.debug("No PDF link for '%s' — skipping", title[:60])
            continue

        source_url = pdf_link["href"]
        if not source_url.startswith("http"):
            source_url = "https://rbidocs.rbi.org.in" + source_url

        if not current_date:
            log.warning("Doc has no date header: '%s' (category: %s)", title[:60], current_category)

        if not _is_kyc_relevant(title, current_category):
            continue

        results.append(
            {
                "title": title,
                "issue_date": current_date,
                "category": current_category,
                "source_url": source_url,
                "source_page": source_page,
            }
        )

    return results


def _scrape_year(session: requests.Session, url: str, post_extras: dict, year: str, source_page: str) -> list[dict]:
    # Fresh GET per year — reusing a chained ViewState causes ASP.NET to silently
    # return the default page instead of the requested year.
    log.debug("GET %s for fresh ViewState (year=%s)", url.split("/")[-1], year)
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    viewstate = _extract_viewstate(BeautifulSoup(resp.text, "lxml"))
    if not viewstate:
        log.error("Could not extract ViewState for year=%s — skipping", year)
        return []

    post_data = {**viewstate, **post_extras, "hdnYear": year, "UsrFontCntr$btn": ""}
    log.debug("POST year=%s to %s", year, url.split("/")[-1])
    resp = session.post(url, data=post_data, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    docs = _parse_page(resp.text, source_page)
    log.info("%-4s  %-20s  %d KYC/AML docs found", year, source_page, len(docs))
    return docs


def _scrape_source(url: str, post_extras: dict, source_page: str, years: list[str]) -> list[dict]:
    session = requests.Session()
    seen_urls: set[str] = set()
    results: list[dict] = []

    log.info("Starting scrape: %s (%d years)", source_page, len(years))
    for year in years:
        time.sleep(1)
        try:
            docs = _scrape_year(session, url, post_extras, year, source_page)
        except requests.RequestException as e:
            log.error("HTTP error fetching %s year=%s: %s", source_page, year, e)
            continue

        dupes = 0
        for doc in docs:
            if doc["source_url"] not in seen_urls:
                seen_urls.add(doc["source_url"])
                results.append(doc)
            else:
                dupes += 1

        if dupes:
            log.debug("year=%s: %d duplicate URLs skipped", year, dupes)

    log.info("Finished %s: %d unique docs total", source_page, len(results))
    return results


def scrape_all() -> list[dict]:
    results = []
    results += _scrape_source(
        "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        {"hdnMonth": "0"},
        "notifications",
        NOTIFICATIONS_YEARS,
    )
    results += _scrape_source(
        "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
        {},
        "master_directions",
        MASTER_DIR_YEARS,
    )
    log.info("scrape_all complete: %d total unique docs", len(results))
    return results


if __name__ == "__main__":
    docs = scrape_all()
    print(json.dumps(docs, indent=2))
