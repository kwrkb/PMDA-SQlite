# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PMDA-SQLite converts Japanese pharmaceutical package insert data from PMDA (Pharmaceuticals and Medical Devices Agency) into queryable SQLite databases. The project supports two database schemas:

1. **Legacy Schema** (`pmda.sqlite`) - Flat structure with all information per product
2. **Improved Schema** (`pmda_v2.sqlite`) - Normalized structure separating medicines, specifications, and interactions

## Database Architecture

### Two Schema Versions

The project maintains two database implementations:

**Legacy (`pmda.sqlite`):**
- 2 tables: `medicines`, `interactions`
- Each product variation (e.g., 10mg vs 50mg tablet) is a separate medicine record
- Dosage form and strength embedded in `product_name` string
- All package insert information duplicated across product variations

**Improved (`pmda_v2.sqlite`):**
- 3 tables: `medicines`, `specifications`, `interactions`
- Medicine information (efficacy, contraindications, etc.) stored once per active ingredient
- Product specifications (dosage form, strength) stored separately
- Enables queries like "all 10mg tablets" or "compare dosage forms for aspirin"

### Key Design Pattern: Specification Separation

The v2 schema recognizes that multiple products (e.g., "Drug X 10mg tablet", "Drug X 50mg tablet") share the same package insert information. This is modeled as:
- One `medicines` record with shared information (generic_name, indications, contraindications, warnings, precautions, pharmacokinetics)
- Multiple `specifications` records for each product variant (product_name, dosage_form, strength, strength_unit)
- `interactions` linked to medicine (not specification) since drug interactions are ingredient-level

## Common Commands

### Database Setup

**Legacy schema:**
```bash
source .venv/bin/activate
python3 src/db_setup.py                    # Create schema
python3 src/load_all_data_to_db.py         # Load all XML data
python3 src/load_pdf_only_data.py          # Add PDF-only products
python3 src/update_additional_fields.py    # Populate extended fields
```

**Improved schema:**
```bash
source .venv/bin/activate
python3 src/db_setup_v2.py                 # Create v2 schema
python3 src/load_data_v2.py 100            # Load first 100 (test)
python3 src/load_data_v2.py                # Load all data (~15-20 min)
```

### Testing Product Name Parser

The product name parser extracts structured data from Japanese product names:
```bash
python3 src/parse_product_name.py          # Run test suite
```

Handles patterns like:
- `ボラニゴ錠10mg` → dosage_form: '錠', strength: 10.0, unit: 'mg'
- `ヘパリン類似物質油性クリーム0.3％` → dosage_form: 'クリーム', strength: 0.3, unit: '%'
- Supports both half-width (%) and full-width (％) percent signs

### Running Examples

```bash
python3 examples/basic_search.py              # Product name search
python3 examples/drug_interactions.py         # Interaction queries
python3 examples/pregnancy_search.py          # Pregnancy precautions
python3 examples/side_effects_search.py       # Side effect queries
python3 examples/statistics.py                # Database statistics
python3 examples/search_by_specification.py   # V2 schema queries
```

## Data Pipeline

### XML Processing Flow

1. **Source:** `data/PMDAraw/pmda_all_20251122/SGML_XML/` (13,432 XML files)
2. **Parse:** `parse_xml_data.py` extracts structured data from XML
3. **Load:** Data inserted into SQLite via `load_all_data_to_db.py` or `load_data_v2.py`

### PDF Fallback

Some products (140) lack XML and require PDF extraction:
- `extract_pdf_data.py` uses OCR (yomitoku package)
- `transform_extracted_data.py` converts OCR output to database format
- `load_pdf_only_data.py` imports PDF-extracted data

### Product Name Parsing (V2 Schema Only)

`parse_product_name.py` uses regex patterns to extract:
- **Dosage form:** Maps variants (錠/錠剤→'錠', カプセル/カプセル剤→'カプセル', DS→'散')
- **Strength:** Decimal or integer followed by unit (mg, g, μg, %, mL, 単位, IU)
- **Normalization:** Converts mcg/μg→'μg', ％→'%'

The parser powers the v2 schema's structured queries by transforming free-text product names into queryable fields.

## Critical Implementation Details

### Character Encoding

- Database: UTF-8
- XML files: UTF-8 with BOM in some cases
- Product names contain full-width characters (％, ０-９) that must be handled correctly

### Deduplication Logic (V2 Schema)

`find_or_create_medicine()` in `load_data_v2.py` checks if `(generic_name, manufacturer)` exists before inserting. If found, reuses existing medicine_id for new specification. This implements the one-medicine-many-specifications pattern.

### Dosage Form Mapping

The `DOSAGE_FORM_MAPPING` dictionary normalizes variations:
- Input: '錠', '錠剤' → Output: '錠'
- Input: 'DS' (dry syrup) → Output: '散'
- Input: 'パッチ', 'テープ', 'パップ' → Output: '貼付剤'

Always check this mapping when adding new dosage form patterns.

### Interaction Data Model

Drug interactions are stored at the medicine (ingredient) level, not specification level. This is correct because interactions depend on the active ingredient, not dosage form or strength.

## File Organization

```
src/
├── db_setup.py              # Legacy schema
├── db_setup_v2.py           # Improved schema
├── parse_xml_data.py        # XML → dict extraction
├── parse_product_name.py    # Product name → specification parser
├── load_all_data_to_db.py   # Legacy data loading
├── load_data_v2.py          # V2 data loading with deduplication
├── update_additional_fields*.py  # Populate extended fields (legacy)
└── extract_pdf_data.py      # OCR for PDF-only products

examples/
├── basic_search.py          # Legacy schema queries
├── search_by_specification.py  # V2 schema specification queries
└── [other examples]         # Specialized queries

docs/
├── DATABASE_SCHEMA.md       # Legacy schema documentation
├── IMPROVED_SCHEMA.md       # V2 schema design rationale
└── SETUP_V2.md             # V2 setup guide
```

## Query Patterns

### Legacy Schema

Products searched by `LIKE` on `product_name`:
```sql
SELECT * FROM medicines WHERE product_name LIKE '%アスピリン%'
```

### V2 Schema

Products searched by structured specification fields:
```sql
-- All 10mg tablets
SELECT * FROM specifications WHERE dosage_form = '錠' AND strength = 10.0

-- Dosage forms for aspirin
SELECT s.* FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE m.generic_name LIKE '%アスピリン%'
ORDER BY s.dosage_form, s.strength
```

## Testing Data

Use limited data loads for testing:
```bash
python3 src/load_data_v2.py 10    # Just 10 products for quick testing
```

Statistics printed after load show:
- Medicine count (unique active ingredients)
- Specification count (product variants)
- Interaction count
- Dosage form distribution

## Important Constraints

### Medical Data Disclaimer

This database is for informational purposes only and must not be used for medical decisions. Always include this warning in user-facing applications.

### Data Freshness

Data snapshot: November 22, 2025. Package inserts are continuously updated by PMDA. The database is a point-in-time snapshot and may not reflect current information.

### NULL Handling

Many fields may be NULL:
- PDF-only products have minimal data (product_name only)
- Not all XML files contain all fields
- V2 schema: Products without parseable strength have NULL strength/strength_unit

Always use `IS NULL` checks in queries.
