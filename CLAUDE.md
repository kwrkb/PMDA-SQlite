# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PMDA-SQLite converts Japanese pharmaceutical package insert data from PMDA (Pharmaceuticals and Medical Devices Agency) into a queryable SQLite database with a normalized schema.

## Database Architecture

The database uses a normalized 3-table schema:

- **medicines**: Core drug information (generic_name, manufacturer, indications, contraindications, etc.)
- **specifications**: Product variants (product_name, dosage_form, strength, yj_code, etc.)
- **interactions**: Drug interactions linked to medicines (target_name, description, severity)

### Key Design Pattern

Multiple products (e.g., "Drug X 10mg tablet", "Drug X 50mg tablet") share the same package insert information:
- One `medicines` record with shared information
- Multiple `specifications` records for each product variant
- `interactions` linked to medicine (ingredient-level, not product-level)

## Common Commands

### Database Setup

```bash
source .venv/bin/activate
python3 src/db_setup.py       # Create schema
python3 src/load_data.py 10   # Test load (10 directories)
python3 src/load_data.py      # Full load (~2-3 min)
```

### Testing

```bash
python3 src/parse_product_name.py  # Run product name parser tests
```

## File Organization

```
src/
├── config.py              # Shared config (DB path, XML directory auto-detection)
├── db_setup.py            # Database schema creation
├── load_data.py           # XML data loading
├── parse_xml.py           # lxml-based XML parser
├── parse_product_name.py  # Product name parsing (has built-in tests)
├── update_fields.py       # Phase 1 field updates
└── update_changed_data.py # Differential update (template)

docs/
├── V2_ISSUES.md              # Project status
├── XML_NAMESPACE.md          # XML namespace guide
└── SPECIFICATION_COMPLIANCE.md # PMDA XML spec compliance

data/
└── pmda.sqlite            # Database file
```

## Data Pipeline

### XML Processing Flow

1. **Source:** `data/PMDAraw/pmda_all_sgml_xml_*/SGML_XML/` (auto-detected)
2. **Parse:** `parse_xml.py` extracts data using lxml with proper namespace handling
3. **Load:** `load_data.py` inserts data with deduplication

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

### Namespace Handling

PMDA XML requires this namespace declaration:
```python
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}
```

Wrong namespaces silently fail to extract data.

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
```

## Database Statistics (2026-01-15)

| Item | Count |
|------|-------|
| Medicines (package inserts) | 9,132 |
| Specifications (products) | 16,726 |
| Interactions | 6,925 |

## Important Constraints

### Medical Data Disclaimer

This database is for informational purposes only and must not be used for medical decisions.

### Data Freshness

The database is a point-in-time snapshot. To update:
```bash
rm data/pmda.sqlite
python3 src/db_setup.py
python3 src/load_data.py
```

### NULL Handling

Many fields may be NULL. Always use `IS NULL` checks in queries.
