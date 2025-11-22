# Project: PMDA-SQlite

## Project Overview

This project builds a SQLite database from medical package insert information issued by the PMDA (Pharmaceuticals and Medical Devices Agency). The project extracts data from both **structured XML files** (primary source) and **PDF documents via OCR** (fallback), processing and storing the data in a relational database format.

The database contains comprehensive medicine information including:
- Basic drug information (product name, generic name, manufacturer, etc.)
- Clinical information (indications, dosage, contraindications, side effects)
- Drug interaction data (contraindicated and cautionary combinations)

## Data Sources

The project processes data from two sources, prioritizing XML for accuracy:

1. **XML Files (Primary)**: ~13,566 structured XML files from PMDA
   - Located in `data/PMDAraw/pmda_all_20251122/SGML_XML/`
   - Provides highly accurate, structured data
   - Includes detailed drug interaction information

2. **PDF Files (Fallback)**: OCR processing via `yomitoku`
   - Used only when XML data is unavailable
   - Located in `data/PMDAraw/pmda_all_20251122/PDF/`
   - Processed output stored in `data/output/`

## Database Schema

The database `pmda.sqlite` contains two main tables:

1.  `medicines`: Stores basic information for each drug.
    *   `id`: Primary Key
    *   `product_name`: Product Name
    *   `generic_name`: Generic Name
    *   `manufacturer`: Manufacturer
    *   `revision_date`: Revision Date of the package insert
    *   `jsc_code`: Japan Standard Commodity Classification Code
    *   `indications`: Indications and effects
    *   `dosage`: Dosage and administration
    *   `contraindications`: Contraindications
    *   `side_effects`: Side effects
    *   `source_file`: The name of the source file
    *   `created_at`: Timestamp of when the record was created

2.  `interactions`: Stores information about drug interactions.
    *   `id`: Primary Key
    *   `medicine_id`: Foreign key referencing the `id` in the `medicines` table.
    *   `target_name`: The name of the interacting drug or component.
    *   `description`: A description of the interaction (clinical symptoms, mechanism, treatment method).

## Project Components

### Data Processing Scripts

1. **`src/db_setup.py`**: Database initialization
   - Creates `pmda.sqlite` and required tables

2. **`src/parse_xml_data.py`**: XML data parser
   - Extracts structured data from PMDA XML files
   - Handles product information, indications, dosage, contraindications, side effects
   - Extracts drug interactions (contraindicated and cautionary combinations)

3. **`src/extract_pdf_data.py`**: PDF OCR processing
   - Uses `yomitoku` to extract text from PDF files
   - Outputs JSON format with text layout information

4. **`src/transform_extracted_data.py`**: OCR data transformation
   - Parses yomitoku JSON output
   - Extracts medicine information using pattern matching and heuristics
   - Fallback when XML data is unavailable

5. **`src/load_all_data_to_db.py`**: Unified data loading
   - **Primary**: Loads data from XML files
   - **Fallback**: Loads data from OCR JSON when XML is unavailable
   - Inserts medicine and interaction data into database

6. **`src/load_existing_json_to_db.py`**: OCR-only data loading
   - Loads pre-processed OCR JSON files
   - Used for testing or when only OCR data is available

## Building and Running

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Complete Pipeline

1. **Initialize Database:**
```bash
python3 src/db_setup.py
```

2. **Load All Data (XML + OCR fallback):**
```bash
# Load all data (recommended)
python3 src/load_all_data_to_db.py

# Or load limited number for testing (e.g., 100 records)
python3 src/load_all_data_to_db.py 100
```

### Alternative: OCR-Only Pipeline

If you only have PDF files or want to test OCR processing:

1. **Extract PDF data with OCR:**
```bash
python3 src/extract_pdf_data.py
```

2. **Load OCR data to database:**
```bash
# Load all OCR JSON files
python3 src/load_existing_json_to_db.py

# Or load limited number
python3 src/load_existing_json_to_db.py 10
```

## Data Quality

The unified loading script prioritizes XML data for superior quality:

**XML Data** (when available):
- 100% accuracy for structured fields
- Complete drug interaction details
- Proper categorization of contraindications vs. cautions

**OCR Data** (fallback):
- ~95-97% extraction rate for major fields (indications, dosage, side effects)
- ~72% extraction rate for contraindications
- Less accurate interaction parsing due to unstructured text

## Current Status

- ✅ Database schema designed and implemented
- ✅ XML parser fully implemented
- ✅ OCR extraction pipeline implemented
- ✅ Unified data loading system (XML priority + OCR fallback)
- 🔄 Full data load in progress (~13,566 XML files + 272 OCR files)

## Development Conventions

*   **Language:** Python 3.12+
*   **Database:** SQLite 3
*   **Directory Structure:**
    *   `src/`: Python source code
    *   `data/PMDAraw/`: Raw data from PMDA
        *   `SGML_XML/`: XML files (primary source)
        *   `PDF/`: PDF files (for OCR fallback)
    *   `data/output/`: Processed OCR JSON files
*   **Dependencies:** See `requirements.txt`
    - `yomitoku`: OCR processing
