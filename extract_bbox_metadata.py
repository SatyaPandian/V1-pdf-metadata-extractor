import argparse
import json
from collections import Counter

import pdfplumber
import pandas as pd


def clamp_bbox_to_page(bbox, page):
    """
    Ensures bbox is fully inside the page bounds.
    bbox: (x0, top, x1, bottom)
    """
    x0, top, x1, bottom = bbox

    x0 = max(0, min(x0, page.width))
    x1 = max(0, min(x1, page.width))
    top = max(0, min(top, page.height))
    bottom = max(0, min(bottom, page.height))

    if x1 < x0:
        x0, x1 = x1, x0
    if bottom < top:
        top, bottom = bottom, top

    return (x0, top, x1, bottom)


def bbox_overlap(a, b):
    ax0, at, ax1, ab = a
    bx0, bt, bx1, bb = b

    inter_w = max(0, min(ax1, bx1) - max(ax0, bx0))
    inter_h = max(0, min(ab, bb) - max(at, bt))
    return inter_w > 0 and inter_h > 0


def extract_bbox_text_metadata(pdf_path, page_number, bbox):
    """
    Extract line-level metadata from text inside a bounding box.
    bbox format: (x0, top, x1, bottom)
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        bbox = clamp_bbox_to_page(bbox, page)
        cropped = page.crop(bbox)

        words = cropped.extract_words(
            keep_blank_chars=False,
            use_text_flow=True,
            extra_attrs=["fontname", "size"]
        )

        if not words:
            return {
                "page_number": page_number,
                "bbox": bbox,
                "lines": [],
                "message": "No text found inside bbox"
            }

        wdf = pd.DataFrame(words)
        wdf["line_id"] = wdf["top"].round(0)

        lines_df = (
            wdf.sort_values(["line_id", "x0"])
              .groupby("line_id")
              .agg({
                  "text": lambda x: " ".join(x),
                  "fontname": lambda x: Counter(x).most_common(1)[0][0],
                  "size": lambda x: Counter(x).most_common(1)[0][0],
                  "x0": "min",
                  "top": "min",
                  "x1": "max",
                  "bottom": "max",
              })
              .reset_index(drop=True)
              .sort_values("top")
        )

        return {
            "page_number": page_number,
            "bbox": bbox,
            "lines": lines_df.to_dict(orient="records")
        }


def extract_bbox_image_metadata(pdf_path, page_number, bbox):
    """
    Returns embedded images that intersect bbox.
    bbox format: (x0, top, x1, bottom)
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        bbox = clamp_bbox_to_page(bbox, page)

        results = []
        for i, img in enumerate(page.images):
            img_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])

            if bbox_overlap(bbox, img_bbox):
                results.append({
                    "image_id": i,
                    "image_bbox": img_bbox,
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "name": img.get("name"),
                    "srcsize": img.get("srcsize"),
                })

        return {
            "page_number": page_number,
            "bbox": bbox,
            "image_count": len(results),
            "images": results
        }


def extract_bbox_table_signal(pdf_path, page_number, bbox):
    """
    Returns lightweight signals to guess if bbox contains a table/grid.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        bbox = clamp_bbox_to_page(bbox, page)
        cropped = page.crop(bbox)

        return {
            "page_number": page_number,
            "bbox": bbox,
            "lines_count": len(cropped.lines),
            "rects_count": len(cropped.rects),
            "curves_count": len(cropped.curves),
            "likely_table": (len(cropped.lines) + len(cropped.rects)) > 15
        }


def extract_bbox_metadata(pdf_path, page_number, bbox):
    text_part = extract_bbox_text_metadata(pdf_path, page_number, bbox)
    image_part = extract_bbox_image_metadata(pdf_path, page_number, bbox)
    table_part = extract_bbox_table_signal(pdf_path, page_number, bbox)

    return {
        "pdf_path": pdf_path,
        "page_number": page_number,
        "bbox": text_part.get("bbox", bbox),
        "text": text_part.get("lines", []),
        "text_line_count": len(text_part.get("lines", [])),
        "images": image_part.get("images", []),
        "image_count": image_part.get("image_count", 0),
        "table_signal": table_part
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract metadata from a PDF region (bbox) without PyMuPDF."
    )

    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--page", type=int, required=True, help="Page number (0-indexed)")
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        required=True,
        metavar=("x0", "top", "x1", "bottom"),
        help="Bounding box coordinates (pdfplumber coords)"
    )
    parser.add_argument("--out", default=None, help="Output JSON file path (optional).")

    args = parser.parse_args()

    bbox = tuple(args.bbox)
    result = extract_bbox_metadata(args.pdf, args.page, bbox)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved output to: {args.out}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
