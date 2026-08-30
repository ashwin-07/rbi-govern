import time
from pathlib import Path
from urllib.parse import urlparse

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

PDF_DIR = Path(__file__).parents[2] / "data" / "pdfs"


def download_pdfs(docs: list[dict]) -> list[str]:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    local_paths = []

    for i, doc in enumerate(docs):
        url = doc["source_url"]
        filename = Path(urlparse(url).path).name
        dest = PDF_DIR / filename

        if dest.exists():
            local_paths.append(str(dest))
            continue

        if i > 0:
            time.sleep(1)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            local_paths.append(str(dest))
        except requests.RequestException as e:
            print(f"Failed to download {url}: {e}")

    return local_paths
