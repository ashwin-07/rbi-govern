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

PAGES = [
    ("https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx", "master_directions"),
    ("https://www.rbi.org.in/Scripts/NotificationUser.aspx", "notifications"),
]

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


def _is_kyc_relevant(title: str, category: str) -> bool:
    combined = (title + " " + category).lower()
    return any(term in combined for term in KYC_TERMS)


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


def scrape_all() -> list[dict]:
    all_docs = []

    for i, (url, source_page) in enumerate(PAGES):
        if i > 0:
            time.sleep(1)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        docs = _parse_page(resp.text, source_page)
        all_docs.extend(docs)

    return all_docs


if __name__ == "__main__":
    docs = scrape_all()
    print(json.dumps(docs, indent=2))
