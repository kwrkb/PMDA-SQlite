# Project: PMDA-SQlite

## Project Overview

This project aims to build a SQLite database from information contained in medical package inserts issued by the PMDA (Pharmaceuticals and Medical Devices Agency). The primary goal is to extract data from PDF documents, process it, and store it in a structured relational format. The database is designed to hold not only basic information about medicines but also details about drug interactions.

The project uses Python and the built-in `sqlite3` library for database management. Data extraction from PDF files is planned to be performed using the `yomitoku` OCR tool.

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
    *   `source_file`: The name of the source PDF file
    *   `created_at`: Timestamp of when the record was created

2.  `interactions`: Stores information about drug interactions.
    *   `id`: Primary Key
    *   `medicine_id`: Foreign key referencing the `id` in the `medicines` table.
    *   `target_name`: The name of the interacting drug or component.
    *   `description`: A description of the interaction (e.g., "Contraindicated for concurrent use," "Caution for concurrent use").

## Building and Running

As the project is in its initial phase, there is no single command to run the entire pipeline. The current workflow is as follows:

1.  **Setup the Database:**
    *   Run the setup script to create the `pmda.sqlite` file and the required tables.
    ```bash
    python3 src/db_setup.py
    ```

2.  **Add Data Files:**
    *   Place the PDF files of the medical package inserts into the `data/pdf/` directory.

3.  **TODO: Data Extraction and Loading:**
    *   A script needs to be created to perform the following steps:
        *   Iterate through PDF files in `data/pdf/`.
        *   Use the `yomitoku` OCR tool to extract text and layout information from each PDF.
        *   Parse the OCR output.
        *   Populate the `medicines` and `interactions` tables in the `pmda.sqlite` database.

## Development Conventions

*   **Language:** Python 3.
*   **Database:** SQLite.
*   **Directory Structure:**
    *   `src/`: Contains all Python source code.
    *   `data/`: Contains data files, with subdirectories for different formats (e.g., `pdf`).
*   **Dependencies:** The project will require the `yomitoku` package. A `requirements.txt` file should be created to manage dependencies.
    ```bash
    # TODO: Create requirements.txt
    pip install yomitoku
    ```
