# PDF Bounding Box Metadata Extractor (No PyMuPDF)

Python utility to extract metadata from a **given bounding box** inside a PDF page.

This was built as an assignment to extract:
- **Text metadata** (line text + font name + font size + bbox coordinates)
- **Image metadata** (embedded images intersecting bbox)
- **Basic table/grid signal** (vector line/rect/curve counts)

## Features
- Works with `pdfplumber` + `pypdf`
- Accepts bbox as input (assumes bbox comes from UI/user)

## Output (JSON)
Returns structured JSON containing:
- page number + bbox (clamped safely to page bounds)
- extracted text lines + font info
- detected embedded images metadata
- table signal heuristics

## Install
```bash
pip install -r requirements.txt
```
Usage (CLI)
```
python extract_bbox_metadata.py --pdf "file.pdf" --page 0 --bbox 0 0 400 200 --out output.json
```
Notebook

See: notebooks/V1_pdf_metadata_extractor.ipynb
