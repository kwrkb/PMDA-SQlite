# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PMDA-SQLite converts Japanese pharmaceutical package insert data from PMDA (Pharmaceuticals and Medical Devices Agency) into a queryable SQLite database with a normalized schema.

## Database Architecture

The database uses a normalized 3-table schema:

- **medicines**: Core drug information — 37 columns covering all 35 XML sections (generic_name, manufacturer, indications, adverse_events, use_in_pregnant, etc.)
- **specifications**: Product variants (product_name, dosage_form, strength, yj_code, etc.)
- **interactions**: Drug interactions linked to medicines (target_name, description, severity)

### Key Design Pattern

Multiple products (e.g., "Drug X 10mg tablet", "Drug X 50mg tablet") share the same package insert information:
- One `medicines` record with shared information
- Multiple `specifications` records for each product variant
- `interactions` linked to medicine (ingredient-level, not product-level)

## Common Commands

### Database Setup (recommended: JSON pipeline)

```bash
source .venv/bin/activate

# Phase 1: XML → JSON変換（初回のみ）
PYTHONPATH=src python3 src/xml_to_json.py

# Phase 2: JSON → SQLite
PYTHONPATH=src python3 src/db_setup.py
PYTHONPATH=src python3 src/json_to_db.py 10   # Test load (10 directories)
PYTHONPATH=src python3 src/json_to_db.py       # Full load (~30 sec)
```

### Testing

```bash
python3 src/parse_product_name.py  # Run product name parser tests
```

### Validation

```bash
PYTHONPATH=src python3 src/validate_json.py  # JSON quality report
```

## File Organization

```
src/
├── config.py              # Shared config (DB path, XML/JSON directory paths)
├── db_setup.py            # Database schema creation (37-column medicines table)
├── xml_to_json.py         # Phase 1: XML → JSON lossless conversion
├── validate_json.py       # JSON quality report & section coverage
├── json_to_db.py          # Phase 2: JSON → SQLite loader (all 35 sections)
├── parse_product_name.py  # Product name parsing (has built-in tests)
├── parse_xml.py           # [DEPRECATED] lxml-based XML parser
└── load_data.py           # [DEPRECATED] XML data loading

docs/
├── V2_ISSUES.md              # Project status
├── XML_NAMESPACE.md          # XML namespace guide
└── SPECIFICATION_COMPLIANCE.md # PMDA XML spec compliance

data/
├── pmda.sqlite            # Database file
└── json/                  # JSON intermediate files (18,023 files)
```

## Data Pipeline

### JSON Intermediate Pipeline (current)

```
XML (data/PMDAraw/) → [xml_to_json.py] → JSON (data/json/)
                                            ↓
                                      [json_to_db.py]
                                            ↓
                                      SQLite (data/pmda.sqlite)
```

1. **Phase 1 — XML → JSON**: `xml_to_json.py` converts all XML to lossless JSON (one-time)
2. **Phase 2 — JSON → SQLite**: `json_to_db.py` loads JSON into the extended schema

### medicines Table Columns

| Category | Columns |
|----------|---------|
| Basic | generic_name, manufacturer, revision_date, source_file |
| Metadata | package_insert_no, company_identifier, sccj_no, therapeutic_classification |
| Existing sections | indications, dosage, contraindications, warnings, important_precautions, efficacy_precautions, other_precautions, overdosage, pharmacokinetics |
| UseInSpecificPopulations (8) | use_in_pregnant, use_in_nursing, pediatric_use, use_in_the_elderly, use_in_patients_with_complications, patients_with_hepatic_impairment, patients_with_renal_impairment, males_and_females_of_reproductive_potential |
| New sections (16) | adverse_events, efficacy_pharmacology, precautions_for_application, physchem_of_act_ingredients, results_of_clinical_trials, precautions_for_handling, info_precautions_dosage, influence_on_laboratory_values, conditions_of_approval, attention_of_insurance, reference_information, specially_described_items, main_literature, addressee_of_literature_request, package_info, composition_and_property |

### Multi-Product XML Support

Some XML files contain multiple product specifications. The parser handles this:
- Each `DetailBrandName` element becomes a separate specification entry
- Common data (generic_name, efficacy, etc.) is shared across all products

### Generic Name Extraction

Priority-based extraction:
1. `GenericName/Detail/Lang` - Primary source
2. `GenericName//Lang` - Fallback for nested structures
3. `TherapeuticClassification` - Final fallback

Invalid values (`-`, `－`, `―`, empty) trigger fallback.

## Critical Implementation Details

### Deduplication Logic

`find_or_create_medicine()` returns `(medicine_id, is_new)`:
- Checks if `(generic_name, manufacturer)` exists
- Only inserts interactions when `is_new=True`
- Prevents duplicate interaction data

### JSON Structure (xml_to_json.py output)

Each JSON node has: `_tag`, `_text`, `_tail`, `_attrib`, `_children`, `_comment`, `_pi`.
Key helper functions in `json_to_db.py`:
- `extract_text(node)` — recursively concatenate all text
- `find_section(data, tag)` — find top-level section by tag name
- `find_subsection(data, parent, child)` — find nested section

### Dosage Form Mapping

`DOSAGE_FORM_MAPPING` normalizes variants:
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

-- Full-text search (FTS5)
SELECT product_name, generic_name
FROM medicines_fts
WHERE medicines_fts MATCH 'high blood pressure keyword'

-- Adverse events for a drug
SELECT m.generic_name, m.adverse_events
FROM medicines m
WHERE m.generic_name LIKE '%ワルファリン%'
```

## Database Statistics (2026-02-10)

| Item | Count |
|------|-------|
| Medicines (package inserts) | 9,888 |
| Specifications (products) | 17,849 |
| Interactions | 37,053 |

## Important Constraints

### Medical Data Disclaimer

This database is for informational purposes only and must not be used for medical decisions.

### Data Freshness

The database is a point-in-time snapshot. To update:
```bash
rm data/pmda.sqlite
PYTHONPATH=src python3 src/db_setup.py
PYTHONPATH=src python3 src/json_to_db.py
```

### NULL Handling

Many fields may be NULL. Always use `IS NULL` checks in queries.
