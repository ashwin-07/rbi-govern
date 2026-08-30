import re
from src.ingest.scraper import scrape_all
from src.ingest.downloader import download_pdfs
from src.ingest.extractor import extract_text_pymupdf
from src.db import insert_document

# Matches formats like:
#   RBI/2021-22/123
#   DBOD.No.BP.BC.12/21.04.048/2020-21
#   FIDD.CO.FSD.BC.No.12/05.02.001/2019-20
_CIRCULAR_RE = re.compile(
    r"\b(RBI/\d{4}-\d{2,4}/\d+|[A-Z]{2,}[\w.]*\.(?:No\.)?\d+/[\d.]+/\d{4}-\d{2,4})\b"
)


def _extract_circular_number(text: str) -> str | None:
    # Search only the first 500 chars — the reference number is always in the header
    match = _CIRCULAR_RE.search(text[:500])
    return match.group(1) if match else None


def run():
    print("Scraping RBI listing pages...")
    docs = scrape_all()
    print(f"Found {len(docs)} KYC/AML documents")

    print("Downloading PDFs...")
    local_paths = download_pdfs(docs)
    print(f"Downloaded {len(local_paths)} PDFs")

    print("Extracting text and inserting into Postgres...")
    inserted = 0
    for doc, path in zip(docs, local_paths):
        raw_text = extract_text_pymupdf(path)
        row = {
            "circular_number": _extract_circular_number(raw_text),
            "issue_date": doc["issue_date"] or None,
            "title": doc["title"],
            "category": doc["category"],
            "raw_text": raw_text,
            "source_url": doc["source_url"],
            "source_page": doc["source_page"],
        }
        doc_id = insert_document(row)
        if doc_id:
            inserted += 1
            print(f"  [{doc_id}] {doc['title'][:80]}")

    print(f"\nDone. {inserted} new documents inserted.")


if __name__ == "__main__":
    run()
