# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Canonical Scope

`VISION.md` is the canonical spec: purpose, scope, non-scope, and the design
principles in force. **Read it before proposing architectural changes.** In
particular, the query layer (CLI / REST / MCP server / GUI) is explicitly
out of scope — it belongs to a separate project, and this repository's only
contract to it is schema stability. Resolution order when documents conflict:
`VISION.md` > `PLAN.md` > code > `NOTES.md`; `LESSONS.md` records why past
alternatives were rejected.

## Project Overview

PMDA-SQLite converts Japanese pharmaceutical package insert data from PMDA (Pharmaceuticals and Medical Devices Agency) into a queryable SQLite database with a normalized schema.

Package insert body text is rendered through PMDA's own official XSLT stylesheet
(`vendor/pmda-styles/`) rather than hand-mapped from XML tags, so section numbering,
headings, and table structure match the PMDA website exactly. See
`docs/XSL_SPIKE.md` for the investigation that led to this design.

## Database Architecture

The database uses a normalized 4-table schema:

- **medicines**: Document identity/metadata only (generic_name, manufacturer,
  revision_date, package_insert_no, company_identifier, sccj_no,
  therapeutic_classification). **1 XML file = 1 medicines record**, keyed by
  `package_insert_no` (see "Deduplication" below).
- **specifications**: Product variants (product_name, dosage_form, strength, yj_code, etc.), extracted directly from XML tags (`DetailBrandName`).
- **interactions**: Drug interactions linked to medicines (target_name, description, severity), extracted directly from XML tags.
- **sections**: Body text normalized one row per document section (`section_no`, `heading`, `level`, `body_md` in Markdown), produced by rendering the XML through PMDA's official XSLT and splitting the resulting HTML.
- **`medicines_legacy`** (VIEW): Pivots `sections` back into the old 35-column
  shape (`indications`, `adverse_events`, etc.) for backward-compatible queries.

### Key Design Pattern

Multiple products (e.g., "Drug X 10mg tablet", "Drug X 50mg tablet") share the same package insert information:
- One `medicines` record with shared information
- Multiple `specifications` records for each product variant
- `interactions` linked to medicine (ingredient-level, not product-level)
- `sections` linked to medicine, one row per heading in the rendered document

## Common Commands

### Database Setup (current: XSL pipeline)

```bash
# Windows PowerShell
$env:PMDA_RAW_DIR = "C:\path\to\pmda_all_sgml_xml_YYYYMMDD_parent_dir"  # if not under data/PMDAraw/
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe src\db_setup.py
.venv\Scripts\python.exe src\db_setup.py --recreate  # Drop + recreate (required over a pre-sections DB)
.venv\Scripts\python.exe src\xml_to_db.py 10      # Test load (10 directories)
.venv\Scripts\python.exe src\xml_to_db.py          # Full load (~26 min, parallelized)
```

`db_setup.py` refuses to run over a database built by the pre-`sections`
schema and exits 1 — `CREATE TABLE IF NOT EXISTS` never alters an existing
table, so the old `medicines` (no `UNIQUE(package_insert_no)`, 35 body
columns) would survive and `xml_to_db.py` would then treat every row as
already-loaded (`is_new=False`) and write **zero** `sections` while reporting
success. Pass `--recreate` to drop and rebuild.

The loader is CPU-bound (XSLT rendering is superlinear in document size — see
`docs/XSL_SPIKE.md`) and uses `multiprocessing` across `cpu_count() - 1` workers.
DB writes happen serially in the parent process.

`load_all()` prints a timing breakdown at the end of every load. **Read it
before attributing a slow load to anything other than XSLT.** Measured
2026-08-27, 17,747 files / 27 workers: 1,527s wall at **99.3% parallel
efficiency** — worker wall time totals 40,932s against a 27-way lower bound of
1,516s, i.e. 0.7% overhead. **97.3% of worker time is the XSLT transform**
(39,830s); Markdown conversion 872s, XML parsing 151s, tag extraction 74s.
The serial DB writes cost 261s but overlap with worker compute and do not
extend the run, and pool startup is 0.2s — neither is a bottleneck. Feeding
workers in file-size-descending order (LPT scheduling, to keep the 25s
documents off the tail) was implemented and measured: **1,550s, 1.5% slower**,
so it was reverted. See `LESSONS.md` before re-proposing either.

### Testing

```bash
uv pip install -r requirements-dev.txt   # or: pip install -r requirements-dev.txt
pytest                             # Whole suite (tests/, no PYTHONPATH needed)
pytest tests/test_xml_to_db.py -k savepoint
ruff check .                       # Lint (same config CI runs)

python src/render_xsl.py <xml>     # Not a test — inspect one file's sections by eye
```

Tests live in `tests/` and run without `data/PMDAraw/`: body-rendering tests go
through `tests/fixtures/minimal.xml` (hand-written synthetic XML) and the
committed `vendor/pmda-styles/`. `pyproject.toml` puts `src/` on `pythonpath`.
DB tests build a throwaway SQLite under `tmp_path` — nothing touches
`data/pmda.sqlite`. `PMDA_DB_PATH` overrides the DB path if you want a trial
load out of the way of the real database.

CI (`.github/workflows/ci.yml`) runs `ruff check` plus `pytest` on Python
3.10–3.14 for every push to `main` and every PR.

### Validation

```bash
PYTHONPATH=src python src/check_db_integrity.py   # Integrity + stats report
```

## File Organization

```
vendor/
├── pmda-styles/            # PMDA's official XSLT 1.0 stylesheet (committed, ~80KB)
│   ├── preview_ja.xsl      # Entry point
│   ├── include/preview-include.xsl  # Main template library (2,763 lines)
│   ├── include/label-ja.xml, StandardName.xml, RegulatoryClassification.xml  # required by document()
│   └── SOURCE.md           # Where it came from, known bugs, update procedure
└── pmda-xsd/               # PMDA's XML schema (reference only)

src/
├── config.py              # Shared config (DB path, XSL path, PMDA_RAW_DIR env override)
├── db_setup.py             # Schema creation: medicines/specifications/interactions/sections + medicines_legacy VIEW + trigram FTS5
├── render_xsl.py           # XSLT transform + section splitting + float-rounding fix
├── html_to_markdown.py     # HTML fragment → Markdown converter (no external deps)
├── xml_to_db.py             # Main loader: parallel XSLT render + structured extraction + DB write
├── parse_product_name.py  # Product name parsing
└── check_db_integrity.py  # Integrity/stats report (new schema)

tests/                      # pytest suite (no real-data dependency)
├── conftest.py             # Fixtures: minimal XML, rendered HTML tree, temp DB
├── fixtures/minimal.xml    # Hand-written synthetic package insert
└── test_*.py

docs/
├── XSL_SPIKE.md            # Spike investigation: XSLT feasibility, pitfalls, benchmarks
├── V2_ISSUES.md            # Project status
├── XML_NAMESPACE.md        # XML namespace guide
└── SPECIFICATION_COMPLIANCE.md # PMDA XML spec compliance

data/
└── pmda.sqlite            # Database file (not committed)
```

## Data Pipeline

```
XML (PMDA_RAW_DIR) ──┬──► [XSLT: vendor/pmda-styles] ──► HTML ──► [html_to_markdown] ──► sections rows
                      │
                      └──► [lxml tag extraction: xml_to_db.py] ──► medicines / specifications / interactions rows
```

Both paths run against the **same parsed XML tree** inside one worker process
(`xml_to_db.py:_process_one`) — there is no JSON intermediate layer in the
current pipeline (the old `xml_to_json.py → json_to_db.py` two-phase approach
is deprecated; XSLT needs an XML tree, not a JSON dict).

### Why XSLT instead of hand-mapping tags to text

The deprecated `json_to_db.py:extract_text()` concatenated all descendant text
with spaces, destroying section numbers, tables, and list structure. PMDA
publishes an official XSLT stylesheet that renders XML into the exact HTML
shown on the PMDA website — using it as the source of truth for numbering/
headings/tables is far more faithful than re-deriving them from raw tags.
Full investigation: `docs/XSL_SPIKE.md`.

### Known pitfalls baked into `render_xsl.py` / `html_to_markdown.py`

1. **PMDA's own XSLT has a floating-point bug**: section numbers under
   `UseInSpecificPopulations` render as `9.199999999999999` etc. (IEEE754
   artifact in the stylesheet's own arithmetic). `fix_float_section_no()`
   rounds these — **must round, not truncate** (`9.199999999999999` → `9.2`,
   not `9.1`). The same artifact appears in *body* text as item numbers
   (`9.699999999999999.1 …`), so `transform_xml()` calls `fix_float_artifacts()`
   over the whole tree, not just the `Header-data` map.
   **The rule is deliberately narrow**: the token must have 12+ decimals *and*
   sit within `1e-9` of its 1-decimal rounding. Body text also carries
   *single*-precision artifacts that look similar but must not be touched —
   `19.2000007629395` (= float32 of 19.2, off by 7.6e-7) and especially
   `9.17000007629395`, which rounding to one decimal would turn into `9.2`.
   Plain values like `0.000001` (a concentration) are below the digit floor.
   See `tests/test_render_xsl.py` before loosening either condition.
2. **Cross-reference text is filled in by JavaScript, not by the XSLT**:
   `<a class="HeaderRef" href="#HDR_XXX">` is emitted empty; the visible
   `［10.2 参照］` is inserted at page load by `vendor/pmda-styles/js/preview.js`,
   which looks the target up in the hidden `<div id="Header-data">` map (falling
   back to `（見出し参照切れ）`). The DB pipeline runs no JavaScript, so
   `resolve_header_refs()` reproduces that lookup. **Do not delete the anchor
   and its tail** — the tail is ordinary body text (`。用法の図…`), not just a
   separator comma, so removing it silently drops sentences as well as
   medically relevant cross-references.
3. **Inline images live inside `<p>` and table cells**: the stylesheet renders
   `InlineGraphic` as an `<img>` in the middle of a paragraph. `itertext()`
   drops it (an `img` carries no text), so all inline flattening goes through
   `_inline_parts()` / `_clean_inline_text()`, which substitutes
   `![図](<file>)` in place. Any new branch that assembles inline text must use
   them rather than `itertext()`.
4. **XSLT transform time is superlinear in document size** — roughly
   quadratic in element count (log-log slope ≈ 2.1). Measured 2026-08-27 on the
   17,747-file snapshot, 3 runs each, best-of; reproducible to 1.4%:
   6KB→2.6ms (0.44 ms/KB), 143KB→199ms (1.42), 257KB→4,770ms (19.0),
   **579KB→25,428ms (45.0)**. The hot spot is the `ns:CommentRef` template at
   `vendor/pmda-styles/include/preview-include.xsl:2056-2062`, which runs three
   full-document `//ns:Comment` scans **per *resolvable* `CommentRef`**, each
   with an `ancestor::ns:Lang` walk on every hit. A dangling reference costs
   only the first scan: the `xsl:when` guard evaluates to false and control
   falls to `xsl:otherwise`, which emits `（注釈参照切れ）` without running the
   `for-each`. The stylesheet defines no `xsl:key` anywhere. Cost tracks
   Comment count (0→7→25→208 across the rows above).
   Consequences: 200KB+ files are 5.45% of the corpus but ~80% of transform
   cost, and this is why the loader parallelizes with `multiprocessing` instead
   of running serially. Naively rewriting those scans as `key()` **changes the
   output HTML** and does not speed anything up — see issue #2 before trying it.

### Figure images

~80% of package insert directories (95,226 files across 14,487 directories)
ship `.gif`/`.jpg` images alongside the XML. The rendered HTML references them
as `figures/<filename>`, but files sit flat next to the XML (no `figures/`
subdirectory) — `html_to_markdown._fix_img_src()` strips that prefix. Only the
filename reference is stored in `body_md`; images themselves are not copied
into the DB or repo.

### Generic Name Extraction

Priority-based extraction (`xml_to_db.py:extract_generic_name`), which returns
`(name, source)` — the source label tells you which rung it fell to:
1. `GenericName/Detail/Lang` → `"generic_name"` - Primary source
2. `GenericName` full text → `"generic_name"` - Fallback for nested structures
3. `TherapeuticClassification` → `"therapeutic_classification"`
4. First `ApprovalEtc/DetailBrandName/ApprovalBrandName/Lang` (the **brand
   name**) → `"brand_name"` - Last resort

Invalid values (`-`, `－`, `―`, `—`, empty — `INVALID_NAME_VALUES`) trigger fallback.

Rung 4 exists for products that have no generic name at all: blood-preservation
solutions, infusions, allergen diluents (`ACD-A液`, `テルモ血液バッグ`,
`カーミパック生理食塩液`, …). They carry `<GenericName><Detail><Lang>-</Lang>` and
no `TherapeuticClassification`, yet their `PackageInsertNo` and body text are
fine. Before this rung the loader discarded those documents entirely (17 of
17,747). `medicines.generic_name` is `NOT NULL`, so filling it with the brand
name keeps the document; `load_all()` prints how many rows took this path so it
stays visible that those values are brand names, not generic names.

## Critical Implementation Details

### Regulatory classification codes

`specifications.regulatory_classification` is built from
`RegulatoryClassificationCode` values, and the code→label table is **read from
`vendor/pmda-styles/include/RegulatoryClassification.xml`**
(`xml_to_db.load_regulatory_codes`), not hardcoded — it is the same file
PMDA's own stylesheet reads via `document()`
(`preview_ja.xsl:14` → `preview-include.xsl:647`, which selects
`Selection/Item[@id]/Label[@type='preview']/Lang[@xml:lang='ja']`).

The hardcoded table this replaced was wrong for everything except codes 1 and
2: 11–15 were shifted by two (a peritoneal dialysis solution came out as
特定生物由来製品 instead of 処方箋医薬品 — 5,540 rows), and 3–10 / 16–19 had no
entry at all, leaking `コード9`-style placeholders into the DB. **Do not
re-derive this mapping by hand.** Codes 11 and 12 both map to 処方箋医薬品
(only the footnote wording differs); duplicate labels are collapsed.
An unknown code still yields `コード{n}` but now prints a warning once per
process, so a future vendor update that adds codes is visible.

**The same vendor file contains a second, older table** —
`RegulatoryClassifications/RegulatoryClassification/Item[@code]`, which folds
the three 向精神薬 classes into one entry and is therefore shifted by two from
code 9 onward (its `11` is 特定生物由来製品). The replaced hardcoded dict looks
like a copy of that block. `load_regulatory_codes()` anchors at
`Selection/Item` for exactly this reason; loosening the XPath (e.g. to
`.//Item`) silently reintroduces the old mislabeling.

### Deduplication Logic (changed from the deprecated pipeline)

The deprecated `json_to_db.py:find_or_create_medicine()` grouped by
`(generic_name, manufacturer)`, which silently merged genuinely distinct
package inserts — of 18,023 XML files, only 9,888 `medicines` rows were ever
created, discarding ~8,100 documents' body text.

`xml_to_db.py:insert_medicine()` instead keys on **`package_insert_no`**
(`UNIQUE NOT NULL` in the schema), matching "1 XML content = 1 medicines
record". Two XML files with the same `PackageInsertNo` are legitimately the
same document filed under multiple product directories; distinct
`PackageInsertNo` values are always distinct `medicines` rows. Interactions
are inserted once per `medicines` row unconditionally (no `is_new` flag
needed — the identity check upstream already prevents duplicates).

### Comment/PI node handling when walking lxml trees

`xml_to_db.py` walks lxml elements directly (not JSON dicts like the
deprecated pipeline). lxml yields Comment/ProcessingInstruction nodes as
ordinary children with a callable `.tag`, which crashes
`etree.QName(child).localname`. Always filter with `_elements(node)` (defined
in `xml_to_db.py`) before doing tag-name dispatch on iterated children.

### Dosage Form Mapping

`DOSAGE_FORM_MAPPING` (in `parse_product_name.py`) normalizes variants:
- '錠', '錠剤' → '錠'
- 'DS' → '散'
- 'パッチ', 'テープ' → '貼付剤'

## Query Patterns

```sql
-- All 10mg tablets
SELECT * FROM specifications WHERE dosage_form = '錠' AND strength = 10.0

-- Products by generic name
SELECT s.* FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE m.generic_name LIKE '%アスピリン%'

-- Contraindicated interactions
SELECT m.generic_name, i.target_name, i.description
FROM medicines m
JOIN interactions i ON m.id = i.medicine_id
WHERE i.severity = 'contraindication'

-- A document's full body, in order, with numbering/headings intact
SELECT section_no, heading, level, body_md
FROM sections
WHERE medicine_id = ?
ORDER BY ord

-- Full-text search (FTS5, trigram tokenizer — see caveat below)
SELECT m.generic_name, s.section_no, s.heading
FROM sections_fts f
JOIN sections s ON s.id = f.section_id
JOIN medicines m ON m.id = s.medicine_id
WHERE sections_fts MATCH '横紋筋融解症'

-- Backward-compatible: old 35-column style access
SELECT generic_name, adverse_events
FROM medicines_legacy
WHERE generic_name LIKE '%ワルファリン%'
```

### FTS5 trigram caveat

`sections_fts` uses `tokenize='trigram'` (the deprecated `medicines_fts` used
the default `unicode61`, which cannot segment Japanese and made `MATCH`
effectively non-functional for CJK text). Trigram indexes 3-character n-grams,
so **queries shorter than 3 characters return nothing** even when the term is
present (`頻尿`, 2 chars, will not match; `副作用`, 3 chars, works). UI/query
code searching CJK text should fall back to `LIKE` for 1–2 character input.

## Important Constraints

### Medical Data Disclaimer

This database is for informational purposes only and must not be used for medical decisions.

### Data Freshness

The database is a point-in-time snapshot. To rebuild from scratch:
```bash
PYTHONPATH=src python src/db_setup.py --recreate   # or: rm data/pmda.sqlite && ... db_setup.py
PYTHONPATH=src python src/xml_to_db.py
```
Reloading without recreating produces no new `sections`: `insert_medicine()`
returns `is_new=False` for any `package_insert_no` already present, and
`store_result()` skips `interactions`/`sections` in that case (they carry no
UNIQUE constraint, so re-inserting would duplicate rows).

### NULL Handling

Many fields may be NULL. Always use `IS NULL` checks in queries.
`sections.body_md` may legitimately be empty for intermediate/nested headings
that only exist to group child sections (e.g. a brand-name subheading with no
text of its own before its child sections).
