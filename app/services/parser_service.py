import re
import fitz  # PyMuPDF


# система: П1, П2, В1, В12, ВЕ10 и т.д.
SYSTEM_RE = re.compile(r'^\s*([A-ZА-Я]{1,3}\d{1,2}(?:\s?\(.*?\))?)\s*$')

# размер прямоугольный: 500x300 / 500х300
RECT_RE = re.compile(r'(\d{2,4})\s*[xх*×]\s*(\d{2,4})')

# размер круглый: Ø250
ROUND_RE = re.compile(r'[Øø]\s?(\d{2,4})')

# толщина: s=0,5мм / б=0,5мм / 0,5 мм
THICK_RE = re.compile(r'(?:s=|б=)?\s*([0-3](?:[.,]\d)?)\s*мм', re.IGNORECASE)

# единицы измерения
UNIT_RE = re.compile(r'\b(шт|м2|м²|м3|м³|м|кг|компл|комплект|м/кг)\b', re.IGNORECASE)

# количество чаще всего в конце строки
QTY_RE = re.compile(r'(\d+[.,]?\d*)\s*$')


def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_unit(text: str):
    m = UNIT_RE.search(text)
    if not m:
        return None
    return m.group(1).lower().replace("²", "2").replace("³", "3")


def extract_qty(text: str):
    m = QTY_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def extract_thickness(text: str):
    m = THICK_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def extract_shape_and_size(text: str):
    round_match = ROUND_RE.search(text)
    if round_match:
        return "round", None, None, int(round_match.group(1)), f"Ø{round_match.group(1)}"

    rect_match = RECT_RE.search(text)
    if rect_match:
        w = int(rect_match.group(1))
        h = int(rect_match.group(2))
        return "rect", w, h, None, f"{w}x{h}"

    return None, None, None, None, ""


def detect_category(text: str):
    t = text.lower()

    if "крепл" in t or "болт" in t or "гайка" in t or "шайба" in t:
        return None

    if "воздуховод" in t or "отвод" in t or "переход" in t:
        return "duct"

    if "изоляц" in t or "ursa" in t or "bos-solid" in t or "тепло-огнезащит" in t:
        return "insulation"

    if "заслонк" in t:
        return "damper"

    if "лючок" in t or "люк" in t:
        return "hatch"

    if "решетк" in t or "решётк" in t:
        return "grille"

    if "клапан" in t:
        return "valve"

    return "other"


def parse_pdf(path: str):
    items = []
    current_system = "НЕ ОПРЕДЕЛЕНО"

    doc = fitz.open(path)

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")

        for block in blocks:
            raw_text = block[4]
            text = clean_text(raw_text)

            if not text:
                continue

            # новая система
            sys_match = SYSTEM_RE.match(text)
            if sys_match:
                current_system = sys_match.group(1).upper()
                continue

            category = detect_category(text)

            # крепления пропускаем
            if category is None:
                continue

            # берём только то, что нам реально нужно
            if category not in ["duct", "insulation", "damper", "hatch", "grille", "valve", "other"]:
                continue

            unit = extract_unit(text)
            qty = extract_qty(text)
            thickness = extract_thickness(text)
            shape, w_mm, h_mm, d_mm, size_text = extract_shape_and_size(text)

            item = {
                "page": page_num,
                "system": current_system,

                # человеку показываем это
                "name": text,
                "unit": unit,
                "qty": qty,
                "thickness": thickness,

                # тех. поля для математики
                "category": category,
                "shape": shape,
                "w_mm": w_mm,
                "h_mm": h_mm,
                "d_mm": d_mm,

                # чтобы не потерять исходник
                "raw": text
            }

            items.append(item)

    doc.close()
    return items