import json
import re
import time

import requests
from bs4 import BeautifulSoup

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
            continue

        source_url = pdf_link["href"]
        if not source_url.startswith("http"):
            source_url = "https://rbidocs.rbi.org.in" + source_url

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


def _scrape_notifications() -> list[dict]:
    url = "https://www.rbi.org.in/Scripts/NotificationUser.aspx"
    session = requests.Session()

    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    viewstate = _extract_viewstate(soup)

    # collect current year from initial GET
    results = _parse_page(resp.text, "notifications")
    seen_urls = {d["source_url"] for d in results}

    for year in NOTIFICATIONS_YEARS:
        time.sleep(1)
        post_data = {
            **viewstate,
            "hdnYear": year,
            "hdnMonth": "0",
            "UsrFontCntr$btn": "",
        }
        try:
            resp = session.post(url, data=post_data, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch notifications for {year}: {e}")
            continue

        # refresh viewstate for next POST — ASP.NET rotates it each response
        soup = BeautifulSoup(resp.text, "lxml")
        viewstate = _extract_viewstate(soup)

        for doc in _parse_page(resp.text, "notifications"):
            if doc["source_url"] not in seen_urls:
                seen_urls.add(doc["source_url"])
                results.append(doc)

    return results


def _scrape_master_directions() -> list[dict]:
    url = "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx"
    session = requests.Session()

    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    viewstate = _extract_viewstate(soup)

    results = _parse_page(resp.text, "master_directions")
    seen_urls = {d["source_url"] for d in results}

    for year in MASTER_DIR_YEARS:
        time.sleep(1)
        post_data = {
            **viewstate,
            "hdnYear": year,
            "UsrFontCntr$btn": "",
        }
        try:
            resp = session.post(url, data=post_data, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch master directions for {year}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        viewstate = _extract_viewstate(soup)

        for doc in _parse_page(resp.text, "master_directions"):
            if doc["source_url"] not in seen_urls:
                seen_urls.add(doc["source_url"])
                results.append(doc)

    return results


def scrape_all() -> list[dict]:
    results = []
    try:
        results += _scrape_notifications()
    except requests.RequestException as e:
        print(f"Notifications scrape failed: {e}")
    try:
        results += _scrape_master_directions()
    except requests.RequestException as e:
        print(f"Master directions scrape failed: {e}")
    return results


if __name__ == "__main__":
    docs = scrape_all()
    print(json.dumps(docs, indent=2))
