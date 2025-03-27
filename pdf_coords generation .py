import pdfplumber
import json

def train_form_static(filled_form_pdf, mapping_file):
    mapping = []

    with pdfplumber.open(filled_form_pdf) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()  # Extracts all words with bounding box info
            
            for word in words:
                rect = {
                    "text": word["text"],
                    "x0": word["x0"],
                    "y0": word["top"],
                    "x1": word["x1"],
                    "y1": word["bottom"],
                    "page": page_num  # 0-indexed page number
                }
                mapping.append(rect)  # Store all occurrences separately

    # Save to JSON with UTF-8 encoding to avoid Unicode errors
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)

    print(f"Training complete. Field mapping saved to {mapping_file}")

if __name__ == "__main__":
    filled_form_pdf = "filled_form3.pdf"
    mapping_file = "form_mapping_static.json"
    train_form_static(filled_form_pdf, mapping_file)
