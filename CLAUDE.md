# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read these first

Detail that this file used to duplicate now lives in one of these; every rule below cites where its evidence is.

- **`VISION.md`** — canonical spec: purpose, scope, non-scope, design principles. **Read before proposing architectural changes.** The query layer (CLI / REST / MCP server / GUI) is out of scope — it belongs to a separate project, and this repo's only outward contract is schema stability.
- **`LESSONS.md`** — dated record of rejected alternatives and the measurements that killed them. Read before re-proposing an approach; entries are cited below by date.
- **`README.md`** — column-by-column schema, project tree, query examples. Not repeated here.
- **`~/.claude/docs-convention.md`** — the canonical rulebook for VISION / PLAN / LESSONS / NOTES; read it before reading or writing any of them. Consequences that bite most often here: `VISION.md` is not rewritten without user approval, `LESSONS.md` is append-only and gets one entry the moment a plausible alternative is rejected (not a phase-end summary), and code contradicting `VISION.md` is a stop-and-ask. `NOTES.md` does not exist in this repo.

Resolution order when documents conflict: `VISION.md` > `PLAN.md` > code > `NOTES.md`.

## Pipeline shape

Schema: `medicines` / `specifications` / `interactions` / `sections`, plus the `medicines_legacy` VIEW (pivots `sections` back into the old 35-column shape) and the `sections_fts` trigram index. Columns are in `README.md`.

XML splits into two paths inside one worker process (`xml_to_db.py:_process_one`) — there is no JSON intermediate layer (the old `xml_to_json.py → json_to_db.py` pair is deprecated; XSLT needs a tree, not a dict). The file is parsed twice, once per path; at 0.4% of worker time against XSLT's 97.3% that is not worth deduplicating:

- **Body text** → PMDA's official XSLT (`vendor/pmda-styles/`) → HTML → Markdown → `sections` rows. Rendering through the vendor stylesheet rather than hand-mapping tags is why section numbering, headings, and tables match the PMDA website; the deprecated `extract_text()` concatenated descendant text and destroyed all three. Background: `docs/XSL_SPIKE.md`.
- **Structured fields** → direct lxml tag extraction → `medicines` / `specifications` / `interactions` rows.

Multiple products share one package insert: one `medicines` row, many `specifications`; `interactions` and `sections` hang off the medicine (ingredient-level, not product-level). `medicines` is keyed on **`package_insert_no`** (`UNIQUE NOT NULL`) — 1 XML = 1 row. The deprecated pipeline grouped by `(generic_name, manufacturer)` and silently merged distinct documents (18,023 XML → 9,888 rows, ~8,100 documents' body text discarded). Two files sharing a `PackageInsertNo` are the same document filed under several product directories. `LESSONS.md` 2026-07-28 判断4.

## Common Commands

Development happens on **Windows 11 native (not WSL), in PowerShell**, against the in-repo `.venv` managed by `uv`. Every command below is PowerShell with `\` separators; never rewrite them as POSIX (`PYTHONPATH=src python …`, `/mnt/c/…`, `source .venv/bin/activate`), and never install with bare `pip`. `$env:PYTHONPATH` is **not** needed: every entry point lives in `src\`, so Python puts `src\` on `sys.path` as the script directory — including the `--rebuild-fts` child process, which `db_setup.py` spawns as `[sys.executable, <abspath of db_setup.py>, …]`.

```powershell
# Build / rebuild. The DB is a point-in-time snapshot; --recreate is also the refresh path.
$env:PMDA_RAW_DIR = "C:\path\to\pmda_all_sgml_xml_YYYYMMDD_parent_dir"  # only if not under data\PMDAraw\
.venv\Scripts\python.exe src\db_setup.py
.venv\Scripts\python.exe src\db_setup.py --recreate               # DROP + recreate; no need to delete data\pmda.sqlite
.venv\Scripts\python.exe src\xml_to_db.py 10                      # Test load (10 directories)
.venv\Scripts\python.exe src\xml_to_db.py                         # Full load (~26 min, parallelized)

# Verify
.venv\Scripts\python.exe src\check_db_integrity.py                # Integrity + stats, incl. FTS coverage
.venv\Scripts\python.exe src\db_setup.py --rebuild-fts --resume   # Finish a partial FTS index by hand

# Test / lint
uv pip install -r requirements-dev.txt   # uv picks up the .venv in the repo root
.venv\Scripts\pytest.exe                 # Whole suite (tests\, no PYTHONPATH needed)
.venv\Scripts\pytest.exe tests\test_xml_to_db.py -k savepoint
.venv\Scripts\ruff.exe check .           # Lint (same config CI runs)

.venv\Scripts\python.exe src\render_xsl.py <xml>   # Not a test — inspect one file's sections by eye
```

**Verify artifacts, not exit codes**, for any step that can fail silently: the loader read through `| tail` hands you the *pipe's* exit code, not the loader's — which is exactly how an empty `sections_fts` once passed for a successful run. Check `check_db_integrity.py` after every load.

**Run the whole suite — not the tests you think are affected — after touching a lookup/catalog table or a shared path.** Each such table sits in a different module from the tests that pin it: the `RegulatoryClassification` code→label mapping (`xml_to_db.load_regulatory_codes`) and `LEGACY_COLUMN_MAP` (`db_setup.py`, which drives the `medicines_legacy` VIEW) are covered in `tests/test_xml_to_db.py`, `DOSAGE_FORM_MAPPING` (`parse_product_name.py`) in `tests/test_parse_product_name.py`, and `INVALID_NAME_VALUES` (`xml_to_db.py`) only indirectly, through the `extract_generic_name` fallback cases.

Tests need no real data: body rendering goes through `tests/fixtures/minimal.xml` plus the committed `vendor/pmda-styles/`, and DB tests build a throwaway SQLite under `tmp_path` (`$env:PMDA_DB_PATH` overrides the DB path for a trial load). CI (`.github/workflows/ci.yml`) runs `ruff check` + `pytest` on Python 3.10–3.14 for every push to `main` and every PR.

## Loader behaviour

- `db_setup.py` **exits 1 over a pre-`sections` database** instead of upgrading it. `CREATE TABLE IF NOT EXISTS` never alters an existing table, so the old `medicines` would survive, every row would look already-loaded (`is_new=False`), and the run would write **zero** `sections` while reporting success. `--recreate` drops and rebuilds. The same mechanism is why reloading without `--recreate` produces no new `sections`: `store_result()` skips `interactions`/`sections` when `is_new=False`, since neither carries a UNIQUE constraint. `LESSONS.md` 2026-07-31.
- CPU-bound: `multiprocessing` across `cpu_count() - 1` workers, DB writes serial in the parent. `load_all()` prints a timing breakdown — **read it before blaming anything other than XSLT.** Measured 2026-08-27 (17,747 files / 27 workers): parallel efficiency **99.3%**, and **97.3% of worker time is the XSLT transform**; the serial DB writes hide under worker compute. Feeding workers in size-descending order (LPT) was implemented, measured 1.5% slower, and reverted. Full numbers: `LESSONS.md` 2026-08-27.
- lxml yields Comment/ProcessingInstruction nodes as ordinary children with a callable `.tag`, which crashes `etree.QName(child).localname`. Filter with `_elements(node)` before any tag-name dispatch on iterated children.

## Pitfalls baked into `render_xsl.py` / `html_to_markdown.py`

1. **PMDA's own XSLT emits IEEE754 artifacts in its section numbers** (`9.199999999999999`, under `UseInSpecificPopulations`). `transform_xml()` runs `fix_float_artifacts()`, which applies `fix_float_section_no()` across the whole tree rather than only the `Header-data` map — the artifacts show up in body text as item numbers too (`9.699999999999999.1 …`). It **rounds, never truncates** (`→ 9.2`, not `9.1`). The rule is deliberately narrow: 12+ decimals *and* within `1e-9` of the 1-decimal rounding. Body text also carries *single*-precision values that must survive untouched — `19.2000007629395` (float32 of 19.2) and especially `9.17000007629395`, which rounding would turn into `9.2`; `0.000001` (a concentration) is below the digit floor. See `tests/test_render_xsl.py` before loosening either condition.
2. **Cross-reference text is inserted by JavaScript, not by the XSLT.** `<a class="HeaderRef" href="#HDR_XXX">` is emitted empty; `vendor/pmda-styles/js/preview.js` fills in the visible `［10.2 参照］` from the hidden `#Header-data` map at page load. The pipeline runs no JS, so `resolve_header_refs()` reproduces that lookup. **Do not delete the anchor and its tail** — the tail is ordinary body text (`。用法の図…`), so deleting it drops sentences as well as medically relevant cross-references. `LESSONS.md` 2026-07-31.
3. **Inline images live inside `<p>` and table cells.** `itertext()` drops `<img>`, so every inline flattening path goes through `_inline_parts()` / `_clean_inline_text()`, which substitute `![図](<file>)`. Any new branch assembling inline text must use them. `LESSONS.md` 2026-07-31.
4. **`ns:Manufacturer` omits the `level-*` body wrapper** every other section has (`preview-include.xsl:1852-1867` vs 38-101), so `extract_sections()` falls back to the section div itself and `convert_section_body()` skips its nested-section guard for the root only. Narrowing the match back to `level-*` empties 製造販売業者等 (26.x) in *every* document. `LESSONS.md` 2026-08-28.
5. **The XSLT writes body text the flattener must not re-invent.** `<ol>` items carry their own number as `<span class="section_header">2.1 </span>` while the CSS hides the marker (`preview-include.xsl:2361-2365`, `preview.css:100`/`132`) — so `_list_to_markdown()` emits `- ` for `ol` and `ul` alike, never a generated `1.` sequence. `<sup>`/`<sub>` stay as tags (flattening makes `10<sup>5</sup>` read `105`), `<br>` (the XML's `<enter/>`) becomes one space, and `<a class="Link">` becomes `[text](url)` — but not `HeaderRef`, which pitfall 2 already fills. `LESSONS.md` 2026-08-28.
6. **XSLT time is superlinear in document size** — roughly quadratic in element count (0.44 ms/KB at 6KB → 45.0 ms/KB at 579KB). The hot spot is the `ns:CommentRef` template (`vendor/pmda-styles/include/preview-include.xsl:2056-2062`), which runs three full-document `//ns:Comment` scans per *resolvable* ref. 200KB+ files are 5.45% of the corpus but ~80% of transform cost — hence the parallel loader. Rewriting those scans as `xsl:key` was patched and measured: **it changes the output HTML** and is no faster. `LESSONS.md` 2026-08-27, issue #2.

Figure images: ~80% of package insert directories ship `.gif`/`.jpg` alongside the XML (95,226 files / 14,487 dirs). The rendered HTML references `figures/<filename>` but the files sit flat next to the XML — `html_to_markdown._fix_img_src()` strips the prefix. Only the filename reference is stored in `body_md`; images are not copied into the DB or repo.

## Extraction rules

### Generic name

`xml_to_db.extract_generic_name()` returns `(name, source)`; the source label says which rung it fell to. Invalid values (`-`, `－`, `―`, `—`, empty — `INVALID_NAME_VALUES`) fall through to the next rung.

1. `GenericName/Detail/Lang` → `"generic_name"`
2. `GenericName` full text → `"generic_name"` (nested structures)
3. `TherapeuticClassification` → `"therapeutic_classification"`
4. First `ApprovalEtc/DetailBrandName/ApprovalBrandName/Lang` — the **brand name** → `"brand_name"`

Rung 4 exists for products with no generic name at all: blood-preservation solutions, infusions, allergen diluents (`ACD-A液`, `テルモ血液バッグ`, …), which carry `<GenericName><Detail><Lang>-</Lang>` and no `TherapeuticClassification` while their `PackageInsertNo` and body text are fine. `generic_name` is `NOT NULL`, so the brand name keeps 17 otherwise-discarded documents; `load_all()` prints how many rows took this path, so it stays visible that those values are not generic names. A large jump in that count means an extraction bug, not more such products. `LESSONS.md` 2026-08-28.

### Regulatory classification codes

`specifications.regulatory_classification` is built from `RegulatoryClassificationCode` values via `xml_to_db.load_regulatory_codes()`, which reads **`vendor/pmda-styles/include/RegulatoryClassification.xml` at `Selection/Item[@id]/Label[@type='preview']/Lang[@xml:lang='ja']`** — the exact element PMDA's own stylesheet reads (`preview_ja.xsl:14` → `preview-include.xsl:647`), with the XSLT's string-value semantics (descendant text), not `.text`.

**Do not re-derive this mapping by hand, and do not loosen the XPath** (e.g. to `.//Item`): the same file holds a second, older table (`RegulatoryClassifications/RegulatoryClassification/Item[@code]`) that folds the three 向精神薬 classes into one entry and is therefore shifted by two from code 9 on. The hardcoded dict this replaced matched that older block and mislabeled 5,540 rows. Unknown codes still yield `コード{n}`, now with a warning once per process. `LESSONS.md` 2026-08-28 (two entries).

### Dosage form

`DOSAGE_FORM_MAPPING` (`parse_product_name.py`) normalizes variants: '錠'/'錠剤' → '錠', 'DS' → '散', 'パッチ'/'テープ' → '貼付剤'.

## FTS5

- **Trigram tokenizer.** `sections_fts` uses `tokenize='trigram'` (the deprecated `medicines_fts` used `unicode61`, which cannot segment Japanese and made `MATCH` non-functional for CJK). **Queries shorter than 3 characters match nothing** even when the term is present — `頻尿` fails, `副作用` works. Query code should fall back to `LIKE` for 1–2 character CJK input.
- **Index builds crash at random** on SQLite 3.53.1 + Python 3.14 for this corpus (810,095 sections / 103MB of body text): Windows access violation `0xC0000005` or plain segfault, at a different row each run, sometimes not at all. A native abort never reaches `except`. Hence, in `db_setup.py`: `rebuild_fts_index(resume=…)` writes in `FTS_REBUILD_BATCH` (10,000) row transactions — **for reachability, not speed**; a full rebuild does `DROP TABLE` + recreate because a single `DELETE FROM sections_fts` dies too and leaves a half-populated index; and `ensure_fts_index()` runs `db_setup.py --rebuild-fts` as a **child process**, re-invoking it with `--resume` on non-zero exit up to `FTS_REBUILD_MAX_ATTEMPTS`, so one crash costs at most one batch. `load_all()` calls `ensure_fts_index()`, never `rebuild_fts_index()` directly. `LESSONS.md` 2026-08-28.
- **Spawn `--rebuild-fts` with `PMDA_DB_PATH=<abspath>` in the child's env**, as `ensure_fts_index()` does. A child resolving `config.DB_PATH` itself ignores in-process overrides and rebuilds the real database's index.

## Constraints

- **Medical data disclaimer.** This database is for informational purposes only and must not be used for medical decisions.
- **NULL handling.** Many fields may be NULL — use `IS NULL` in queries. `sections.body_md` is legitimately empty for intermediate headings that exist only to group child sections (e.g. a brand-name subheading with no text of its own).
