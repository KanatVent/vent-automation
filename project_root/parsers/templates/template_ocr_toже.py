import fitz
import pytesseract
from PIL import Image
import io
import re
from collections import defaultdict

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

RECT_RE = re.compile(r'(\d{2,4})\s*[xхХ×]\s*(\d{2,4})')
ROUND_RE = re.compile(r'[ØøДдOо°]\s*(\d{2,4})')
THICK_RE = re.compile(r'[дd0δ]=\s*(\d+[.,]\d*)\s*мм', re.IGNORECASE)
TRIPLE_RE = re.compile(r'(\d{2,4})\s*[xхХ×]\s*(\d{2,4})\s*[xхХ×]\s*(\d{2,4})')
TRANSITION_RE = re.compile(
    r'(\d{2,4})\s*[xхХ×]\s*(\d{2,4})\s*[-–]\s*(\d{2,4})\s*[xхХ×]\s*(\d{2,4})'
)
UNIT_RE = re.compile(r'^(м|шт\.?|компл\.?|кг|м2)$', re.IGNORECASE)
QTY_RE  = re.compile(r'^\d+[.,]?\d*$')

DUCT_KEYWORDS = ["воздуховод", "отвод", "переход", "тройник", "труба"]

GARBAGE_KEYWORDS = [
    "решетка", "клапан", "зонт", "лючок", "вентилятор", "глушитель",
    "сталь для крепления", "теплоизоляция", "нагреватель", "фильтр",
    "вставка", "шумоглушитель", "установка", "рельсовая",
    "поставщик", "примечание", "наименование", "обозначение", "формат",
    "изм.", "лист", "подп.", "дата", "масса", "тип,",
    "грунтовка", "краска", "кран", "автоматический", "трубки",
    "труды стальные", "трубы стальные", "дн57", "09х057", "электросварные",
    "тепловая изоляция", "минеральной ваты",
    "листовой", "рельсовая система", "вытяжными",
    "воздухоотводчик", "латунный",
]

def is_garbage(text):
    t = text.lower()
    if any(g in t for g in GARBAGE_KEYWORDS):
        return True
    if re.match(r'^[\d\s.,]+$', text) and len(text) < 4:
        return True
    return False

def get_thickness_by_size(w=None, h=None, d=None):
    sizes = [s for s in [w, h, d] if s is not None]
    if not sizes: return 0.5
    return 0.5 if max(sizes) < 400 else 0.7

def extract_sizes(text, duct_type):
    if "тройник" in duct_type:
        m = TRIPLE_RE.search(text)
        if m:
            nums = sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True)
            return nums[0], nums[1], None
        r = ROUND_RE.search(text)
        if r: return None, None, int(r.group(1))

    if "переход" in duct_type:
        m = TRANSITION_RE.search(text)
        if m:
            w1,h1 = int(m.group(1)), int(m.group(2))
            w2,h2 = int(m.group(3)), int(m.group(4))
            return (w1,h1,None) if (w1+h1)>=(w2+h2) else (w2,h2,None)
        rounds = ROUND_RE.findall(text)
        if len(rounds) >= 2:
            return None, None, max(int(rounds[0]), int(rounds[1]))

    rect = RECT_RE.search(text)
    if rect:
        w1, h1 = int(rect.group(1)), int(rect.group(2))
        if w1 >= 50 and h1 >= 50:
            return w1, h1, None

    r = ROUND_RE.search(text)
    if r: return None, None, int(r.group(1))

    return None, None, None

def calc_area(duct_type, w, h, d, qty, unit):
    if qty is None: return None
    if "воздуховод" in duct_type or "труба" in duct_type:
        if unit and unit.lower() not in ["м", "m"]: return None
        perimeter = (d/1000*3.14) if d else ((w+h)/1000*2 if w and h else None)
        if not perimeter: return None
        return round(perimeter * 1.10 * qty, 2)
    if duct_type in ["отвод", "переход", "тройник"]:
        perimeter = (d/1000*3.14) if d else ((w+h)/1000*2 if w and h else None)
        if not perimeter: return None
        return round(perimeter * 1.10 * 0.6 * qty, 2)
    return None

def ocr_page(page, zoom=3):
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    w, h = img.size

    left  = img.crop((0, 200, 2200, h))
    right = img.crop((2200, 200, w, h))

    left_data  = pytesseract.image_to_data(
        left, lang="rus",
        output_type=pytesseract.Output.DICT
    )
    right_data = pytesseract.image_to_data(
        right, lang="rus",
        output_type=pytesseract.Output.DICT
    )

    left_words  = [(left_data['left'][i],  left_data['top'][i]+200,  left_data['text'][i].strip())
                   for i in range(len(left_data['text'])) if left_data['text'][i].strip()]
    right_words = [(right_data['left'][i]+2200, right_data['top'][i]+200, right_data['text'][i].strip())
                   for i in range(len(right_data['text'])) if right_data['text'][i].strip()]

    return left_words, right_words

def parse_pdf(path):
    doc = fitz.open(path)
    items = []
    current_type = "воздуховод"
    base_text = None

    for page_num, page in enumerate(doc, start=1):
        left_words, right_words = ocr_page(page)

        y_groups = defaultdict(list)
        for x, y, text in left_words:
            y_key = round(y / 18) * 18
            y_groups[y_key].append((x, y, text))

        for y_key in sorted(y_groups.keys()):
            group = sorted(y_groups[y_key], key=lambda r: r[0])
            full_text = " ".join(r[2] for r in group)

            if is_garbage(full_text):
                continue

            full_lower = full_text.lower()

            for kw in DUCT_KEYWORDS:
                if kw in full_lower:
                    current_type = kw
                    base_text = full_text
                    break

            w, h, d = extract_sizes(full_text, current_type)
            if w is None and h is None and d is None:
                continue

            thick_m = THICK_RE.search(full_text)
            if not thick_m and base_text:
                thick_m = THICK_RE.search(base_text)
            thickness = float(thick_m.group(1).replace(",", ".")) if thick_m else get_thickness_by_size(w, h, d)

            unit = qty = None
            best_u = best_q = 40
            for rx, ry, rtext in right_words:
                dy = abs(ry - y_key)
                if dy < best_u and UNIT_RE.match(rtext):
                    best_u = dy
                    unit = rtext
                if dy < best_q and QTY_RE.match(rtext):
                    best_q = dy
                    qty = float(rtext.replace(",", "."))

            if unit is None and current_type == "воздуховод":
                unit = "м"

            area = calc_area(current_type, w, h, d, qty, unit)

            items.append({
                "name": full_text,
                "duct_type": current_type,
                "w": w, "h": h, "d": d,
                "thickness": thickness,
                "unit": unit,
                "qty": qty,
                "area_m2": area,
                "page": page_num
            })

    doc.close()
    return items

def summarize(items):
    summary = {}
    for item in items:
        if item["area_m2"] is None: continue
        t = item["thickness"]
        summary[t] = round(summary.get(t, 0) + item["area_m2"], 2)
    return dict(sorted(summary.items()))

if __name__ == "__main__":
    path = input("Путь к PDF: ").strip().strip('"')
    items = parse_pdf(path)

    print(f"\n{'='*40}")
    print(f"Найдено позиций: {len(items)}")
    print(f"{'='*40}\n")

    for item in items:
        size = (f"{item['w']}x{item['h']}" if item['w']
                else f"Д{item['d']}" if item['d'] else "?")
        print(f"  [{item['duct_type'][:8]}] {size} | "
              f"толщ={item['thickness']}мм | "
              f"{item['qty']} {item['unit']} | "
              f"площадь={item['area_m2']} м2")

    print("\n" + "="*40)
    print("ИТОГ ПО ТОЛЩИНАМ МЕТАЛЛА:")
    print("="*40)
    for thickness, total in summarize(items).items():
        print(f"  {thickness}мм  →  {total} м2")