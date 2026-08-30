# DATA-NOTES

Issues and anomalies found during corpus ingestion. Referenced by Week 2 chunking strategy and Week 3 extraction accuracy measurement.

---

## Corpus snapshot

| Metric | Value |
|---|---|
| Total documents | 34 |
| Source | Notifications only (see §4) |
| Year range | 2015–2025 |
| Documents with usable text (>10KB) | 12 |
| Documents with garbled/minimal text (<5KB) | 22 |
| Documents with `circular_number` populated | 28 |
| Documents with `circular_number = NULL` | 6 |

---

## 1. Garbled text extraction — 22 of 34 documents

**Severity: High.** These documents are effectively unusable for retrieval until fixed.

PyMuPDF extracts corrupted or near-empty text from 22 PDFs. Raw text sizes range from 1.5KB to 5KB where the actual document is several pages. Two failure modes observed:

**Mode A — Mojibake (encoding corruption):** Text is present in the PDF but uses a non-standard or embedded font encoding that PyMuPDF cannot map to Unicode. Output is garbage characters:
```
ž¸¸£÷¸ú¡¸ ¢£{¸¨¸Ä ¤¸ÿˆÅ   RESERVE BANK OF INDIA
¸¾£ ¤¸¾¢ˆ¿ÅŠ¸ ¢¨¸¢›¸¡¸Ÿ¸›¸ ¢¨¸ž¸¸...
```
Affected example: `id=56` — "Amendment to Prevention of Money Laundering..."

**Mode B — Hindi header before English body:** PDFs open with a full Hindi-language header block (Devanagari script). The English circular content begins only after the Hindi section. PyMuPDF extracts both, but the garbled Devanagari occupies the first 300–500 characters, which is exactly where `_extract_circular_number()` searches.

Affected examples: `id=57, 59, 60`

**The 2025 Amendment Directions (ids 67–76):** These are single-page amendment circulars that modify specific clauses of the 2025 Master Directions. Raw text is ~1.5KB — consistent with a genuine one-page document. Not garbled, just short.

> ⚠️ **Fix needed before Week 2:** pdfplumber handles encoding differently from PyMuPDF and recovers text from some of these. Worth running pdfplumber as a fallback on any doc where PyMuPDF returns <5KB.

---

## 2. `circular_number` NULL — 6 documents

**Severity: Medium.** Metadata gap, does not affect retrieval but breaks the amendment graph in Week 3.

The `_extract_circular_number()` regex searches the first 500 characters of raw text. It fails in two situations:

| id | Title (abbreviated) | Reason for NULL |
|---|---|---|
| 56 | Amendment to PML Rules — change in name on marriage | Mojibake in first 500 chars (Mode A above) |
| 57 | Streamlining credit to MSEs | Hindi header pushes circular ref past 500-char window |
| 59 | KYC guidelines — proprietary concerns (Apr 2015) | Hindi header |
| 60 | KYC guidelines — proprietary concerns (Mar 2015) | Hindi header |
| 64 | Digital Payment Transactions — QR Code | Mojibake |
| 78 | Compliance with KYC norms (Nov 2025) | Mojibake |

The circular number formats in circulation across the corpus are:
- `RBI/YYYY-YY/NNN` — most common, matched by regex
- `DBR.AML.BC.No.NN/NN.NN.NNN/YYYY-YY` — matched by regex
- `DOR.AML.REC.No.NN/NN.NN.NNN/YYYY-YY` — matched by regex (newer format from ~2022)

> ⚠️ **Fix needed before Week 3:** Extend the search window beyond 500 chars for docs where the first attempt returns NULL. Alternatively, fall back to scraping the detail page URL (`NotificationUser.aspx?Id=XXXX`) which shows the circular number in structured HTML.

---

## 3. Year gaps in the corpus

**Severity: High.** The amendment graph (Week 3) requires continuity — missing years break the chain.

Years present: 2015, 2016, 2018, 2020, 2021, 2025
Years absent: 2017, 2019, 2022, 2023, 2024

This is almost certainly a scraper issue, not genuine absence of KYC circulars. The RBI issued multiple KYC/AML amendments in 2022–2024 (VCIP expansion, CERSAI integration, updated CDD norms). The year-by-year POST mechanism (`hdnYear` form field) is likely failing silently for those years — the server returns a valid 200 response with the default year's content, which deduplication then filters out entirely.

> ⚠️ **Fix needed:** Add response validation — after each year POST, confirm the returned HTML actually contains dates matching the requested year before accepting the results. Log a warning if it doesn't.

---

## 4. Master Directions page returned zero documents

**Severity: Medium.** All 34 documents came from `NotificationUser.aspx`. The `BS_ViewMasDirections.aspx` scraper returned nothing.

The Master Directions listing uses `GetYear(year)` (no `hdnMonth` field), but our POST form data may be missing a required field specific to that page. The 2016 and 2018 KYC Master Directions that *are* in the corpus came through the Notifications page, not Master Directions — they appear on both pages.

> ⚠️ **Investigate:** Manually inspect what form fields `BS_ViewMasDirections.aspx` expects vs what we're sending.

---

## 5. Tables in PDFs

**Severity: Low.** The KYC Master Direction 2016 contains structured tables (e.g., customer categories, document requirements by risk tier). PyMuPDF extracts these as flat text, losing the row/column structure. `extract_tables_pdfplumber()` recovers table structure but has not been run on the corpus yet.

> **Note for Week 2:** Clause-hierarchy-aware chunking should treat table rows as atomic units, not split mid-row. Run pdfplumber on the two Master Direction documents specifically.

---

## 6. Duplicate title, different content

`id=62` and `id=63` both have the title "Master Direction — Know Your Customer (KYC) Direction, 2016" with the same `circular_number` (`DBR.AML.BC.No.81/14.01.001/2015-16`). They are different editions: one updated to December 2016, one to July 2018. The `source_url` is different (correctly unique), but downstream queries that group by `circular_number` will conflate them.

> **Note for Week 3:** The amendment graph must treat these as distinct nodes with an `amends` edge between them, not as duplicates.
