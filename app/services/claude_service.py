import os
import base64
import json
import re
import io
import httpx
from pdf2image import convert_from_path
import pypdf

os.environ["PATH"] += r";C:\vent_app\poppler\poppler-25.12.0\Library\bin"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """Ты специалист по расчёту вентиляционных систем.
Извлеки из документа все позиции по металлу и изоляции.

ММЕТАЛЛ — считай площадь м² ТОЛЬКО для этих типов (всё остальное игнорируй):
- Воздуховод прямоугольный A×B мм, длина L м: area = (A+B)/1000*2*L*1.10
- Воздуховод круглый D мм, длина L м: area = 3.14159*D/1000*L*1.10
- Переход A×B->C×D, кол-во N шт: area = (A+B)/1000*2*1.10*0.6*N
- Отвод/полуотвод A×B, кол-во N шт: area = (A+B)/1000*2*1.10*0.6*N
- Тройник A×B, кол-во N шт: area = (A+B)/1000*2*1.10*0.7*N
- Зонт A×B мм (если сторона>1000мм), кол-во N шт: area = (A+B)/1000*2*1.10*0.5*N
- Лист оцинкованной стали: area = количество как есть (м²)
ВСЁ ОСТАЛЬНОЕ — не металл. Решётки, диффузоры, крепления — НЕ считай.

ТОЛЩИНА металла: берём из текста (б=0.5, д=0.7 и т.д.)
Если не указано: любая сторона > 400мм -> 0.7мм, иначе -> 0.5мм

ИЗОЛЯЦИЯ: собери всё что связано с утеплением/изоляцией.
Единицы берём как написано (м², м, м³, шт). Никаких формул не применяй.

ИГНОРИРУЙ ПОЛНОСТЬЮ — эти позиции ЗАПРЕЩЕНО включать в результат:
- Решётки (вентиляционные, наружные, алюминиевые, любые)
- Диффузоры, анемостаты
- Вентиляторы, насосы
- Клапаны (любые)
- Крепления, сталь для крепления, шпильки, хомуты
- Шумоглушители, фильтры
Если видишь слово "решётка" или "крепление" — пропускай без исключений.

ФОРМАТ ОТВЕТА - строго только JSON без текста до и после:
{"systems":[{"name":"П1","metal":[{"description":"Воздуховод 400х300","type":"duct","a_mm":400,"b_mm":300,"d_mm":null,"qty":15,"unit":"м","thickness":0.7,"area_m2":15.4}],"insulation":[{"description":"Минвата 50мм","qty":25.5,"unit":"м2"}]}]}

type: duct/transition/elbow/tee/hood/sheet
Если система не указана явно - используй имя "Без системы".
"""


def _is_text_readable(pdf_path: str) -> bool:
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages[:3]:
            text += page.extract_text() or ""

        if len(text.strip()) < 50:
            return False

        broken = len(re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text))
        if broken > 10:
            return False

        cyrillic = len(re.findall(r'[а-яёА-ЯЁ]', text))
        total = len(re.findall(r'\w', text))
        if total == 0:
            return False

        has_kw = any(k in text.lower() for k in ['воздуховод', 'вентил', 'изоляц', 'воздух', 'приток', 'вытяжк'])
        return (cyrillic / total > 0.2) and has_kw
    except:
        return False


def _extract_text(pdf_path: str, pages: str = None) -> str:
    reader = pypdf.PdfReader(pdf_path)
    total = len(reader.pages)

    if pages and pages.strip():
        try:
            parts = pages.strip().split("-")
            start = max(1, int(parts[0])) - 1
            end = min(total, int(parts[1]))
            page_range = range(start, end)
        except:
            page_range = range(total)
    else:
        page_range = range(total)

    text = ""
    for i in page_range:
        page_text = reader.pages[i].extract_text() or ""
        if page_text.strip():
            text += f"\n--- Страница {i+1} ---\n{page_text}"
    return text


def _pdf_to_images(pdf_path: str, pages: str = None, dpi: int = 150) -> list:
    reader = pypdf.PdfReader(pdf_path)
    total = len(reader.pages)

    first_page = 1
    last_page = total

    if pages and pages.strip():
        try:
            parts = pages.strip().split("-")
            first_page = max(1, int(parts[0]))
            last_page = min(total, int(parts[1]))
        except:
            pass

    page_list = convert_from_path(pdf_path, dpi=dpi, first_page=first_page, last_page=last_page)
    images = []
    for page in page_list:
        buf = io.BytesIO()
        page.save(buf, format="PNG")
        images.append(base64.b64encode(buf.getvalue()).decode())
    return images


def _call_claude(content: list) -> str:
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 8000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": content}]
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    resp = httpx.post(API_URL, json=payload, headers=headers, timeout=300)
    resp.raise_for_status()

    data = resp.json()
    text = data["content"][0]["text"]

    if data.get("stop_reason") == "max_tokens":
        text = text + "}]}"

    return text


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise ValueError(f"JSON не найден. Ответ: {text[:500]}")

    json_str = match.group()

    try:
        return json.loads(json_str)
    except:
        pass

    for suffix in ["]}]}", "]}", "}"]:
        try:
            return json.loads(json_str + suffix)
        except:
            continue

    for i in range(len(json_str) - 1, 0, -1):
        if json_str[i] == '}':
            try:
                return json.loads(json_str[:i+1])
            except:
                continue

    raise ValueError("Не удалось распарсить ответ Claude")


def process_pdf(pdf_path: str, pages: str = None) -> dict:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY не установлен")

    if _is_text_readable(pdf_path):
        mode = "text"
        text = _extract_text(pdf_path, pages)
        if not text.strip():
            raise ValueError("Не удалось извлечь текст из PDF")
        content = [{"type": "text", "text": f"Спецификация вентиляции:\n\n{text}"}]
    else:
        mode = "ocr"
        images = _pdf_to_images(pdf_path, pages)
        if not images:
            raise ValueError("Не удалось конвертировать PDF в изображения")
        content = []
        for i, b64 in enumerate(images):
            content.append({"type": "text", "text": f"Страница {i+1}:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64}
            })
        content.append({"type": "text", "text": "Извлеки все позиции по металлу и изоляции из этих страниц."})

    raw = _call_claude(content)
    data = _parse_json(raw)

    summary = {}
    for sys in data.get("systems", []):
        for item in sys.get("metal", []):
            t = str(item.get("thickness", "0.5"))
            a = float(item.get("area_m2", 0) or 0)
            if a > 0:
                summary[t] = round(summary.get(t, 0) + a, 2)

    insulation = []
    for sys in data.get("systems", []):
        for iso in sys.get("insulation", []):
            insulation.append({
                "system": sys.get("name", ""),
                "description": iso.get("description", ""),
                "unit": iso.get("unit", ""),
                "qty": iso.get("qty", 0)
            })

    return {
        "mode": mode,
        "systems": data.get("systems", []),
        "summary_by_thickness": dict(sorted(summary.items())),
        "total_m2": round(sum(summary.values()), 2),
        "insulation": insulation,
    }
