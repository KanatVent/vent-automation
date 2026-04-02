import re
import fitz


RECT_RE = re.compile(r'(\d{2,4})\s*[xх×*]\s*(\d{2,4})')
ROUND_RE = re.compile(r'[Øø]\s*(\d{2,4})')
THICK_RE = re.compile(r'[бbsδ]=?\s*(\d+(?:[.,]\d+)?)\s*мм', re.IGNORECASE)
UNIT_RE = re.compile(r'\b(м2|м²|м)\b', re.IGNORECASE)
QTY_RE = re.compile(r'\b([0-9]+(?:[.,][0-9]+)?)\b')


def clean_text(text):
    text = text.replace("\xa0", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_size(text):

    r = RECT_RE.search(text)
    if r:
        return "rect", int(r.group(1)), int(r.group(2)), None

    r = ROUND_RE.search(text)
    if r:
        return "round", None, None, int(r.group(1))

    return None, None, None, None


def extract_thickness(text):

    m = THICK_RE.search(text)
    if not m:
        return None

    return float(m.group(1).replace(",", "."))


def extract_unit(text):

    m = UNIT_RE.search(text)
    if not m:
        return None

    unit = m.group(1).lower().replace("²", "2")
    return unit


def extract_qty(text):

    numbers = QTY_RE.findall(text)

    if not numbers:
        return None

    try:
        return float(numbers[-1].replace(",", "."))
    except:
        return None


def parse_pdf(path):

    doc = fitz.open(path)

    items = []

    last_base_name = None
    last_base_thickness = None
    current_system = "НЕ ОПРЕДЕЛЕНО"

    for page_num, page in enumerate(doc, start=1):

        lines = page.get_text("text").splitlines()

        for raw in lines:

            text = clean_text(raw)

            if not text:
                continue

            low = text.lower()

            # система
            if re.match(r'^[А-ЯA-Z]{1,3}\d{1,2}$', text):
                current_system = text
                continue

            # базовая строка воздуховодов
            if "воздуховод" in low or "переход" in low:

                last_base_name = text
                last_base_thickness = extract_thickness(text)

                continue

            # строки "То же"
            if low.startswith("то же") and last_base_name:

                shape, w, h, d = extract_size(text)
                unit = extract_unit(text)
                qty = extract_qty(text)

                if shape:

                    items.append({
                        "page": page_num,
                        "system": current_system,
                        "name": last_base_name,
                        "unit": unit if unit else "м",
                        "qty": qty if qty else 0,
                        "thickness": last_base_thickness,
                        "shape": shape,
                        "w_mm": w,
                        "h_mm": h,
                        "d_mm": d,
                        "raw": text
                    })

                continue

            # продолжение базовой строки
            if last_base_name:

                shape, w, h, d = extract_size(text)
                unit = extract_unit(text)
                qty = extract_qty(text)

                if shape:

                    items.append({
                        "page": page_num,
                        "system": current_system,
                        "name": last_base_name,
                        "unit": unit if unit else "м",
                        "qty": qty if qty else 0,
                        "thickness": last_base_thickness,
                        "shape": shape,
                        "w_mm": w,
                        "h_mm": h,
                        "d_mm": d,
                        "raw": text
                    })

    doc.close()

    return items