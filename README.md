
# Motor Claim AI Report System — Version 0.1

## Purpose
Prototype for:
Upload Document (Estimate/Invoice/etc.) + RC → extract data → editable item grid → select/unselect → PMG → depreciation → Excel.

## Important
This is a **prototype**, not the final production AI extraction engine.

The current parser demonstrates the workflow against the supplied invoice formats. Production Version 0.2 should add:
- AI-based document classification
- OCR for scanned PDFs/images
- robust table extraction across arbitrary workshops
- RC OCR
- exact mapping into the user's existing Interim/Tata Excel templates
- calculation validation against the existing workbook formulas
- claim/project database

## Run on Windows
1. Install Python 3.11+.
2. Open Command Prompt in this folder.
3. Run:
   `pip install -r requirements.txt`
4. Run:
   `streamlit run app.py`
5. Chrome will open the application.

## Workflow
1. Upload PDF/image documents.
2. Upload RC if available.
3. Click Extract Data.
4. Verify/edit document and vehicle details.
5. Review all extracted line items.
6. Select/unselect items.
7. Edit description, part number, HSN/SAC, PMG, quantity, rate, taxable amount and GST.
8. Verify depreciation.
9. Generate Assessment Excel.

## Agreed rules
- Metal (M): age-based depreciation
- Plastic (P): 50%
- Glass (G): 0%
- Metal age table:
  - <= 6 months: 0%
  - >6 months to 1 year: 5%
  - >1 to 2 years: 10%
  - >2 to 3 years: 15%
  - >3 to 4 years: 25%
  - >4 to 5 years: 35%
  - >5 to 10 years: 40%
  - >10 years: 50%
