import re


def detect_thickness(name, w_mm=None, h_mm=None):
    text = (name or "").lower()

    # ищем явно указанную толщину: б=0,7мм / s=0,9мм / δ=1,2мм
    match = re.search(r'[бbsδ]=?\s*(\d+(?:[.,]\d+)?)\s*мм', text)
    if match:
        return float(match.group(1).replace(",", "."))

    # если нет — правило сторон
    if w_mm is not None and h_mm is not None:
        if w_mm > 400 or h_mm > 400:
            return 0.7
        return 0.5

    return None


def calc_rect_duct(w_mm, h_mm, length_m):
    w = w_mm / 1000
    h = h_mm / 1000

    area = (w + h) * 2 * length_m
    area = area + area * 0.10

    return round(area, 1)


def calc_round_duct(d_mm, length_m):
    d = d_mm / 1000

    area = 3.14 * d * length_m
    area = area + area * 0.10

    return round(area, 1)


def calc_elbow_or_transition(w_mm, h_mm):
    w = w_mm / 1000
    h = h_mm / 1000

    perimeter = (w + h) * 2
    perimeter = perimeter + perimeter * 0.10
    area = perimeter * 0.6

    return round(area, 1)


def is_ready_m2_item(item: dict) -> bool:
    """
    Уже готовая строка, где площадь дана в м2 и её просто надо добавить.
    Пример:
    Листовая сталь б=0,7мм для коробок под решетки м2 2
    """
    unit = (item.get("unit") or "").lower()
    name = (item.get("name") or "").lower()

    if unit not in ["м2", "m2"]:
        return False

    return (
        "листовая сталь" in name
        or "сталь" in name
    )


def is_countable_item(item: dict) -> bool:
    """
    Считаем только:
    - воздуховоды
    - отводы
    - переходы
    - готовые строки м2 металла
    """
    name = (item.get("name") or "").lower()

    if is_ready_m2_item(item):
        return True

    return (
        "воздуховод" in name
        or "воздуховоды" in name
        or "отвод" in name
        or "переход" in name
    )


def calculate_item(item: dict):
    name = (item.get("name") or "").lower()

    if not is_countable_item(item):
        return None

    qty = item.get("qty")

    if qty is None:
        return None

    # если строка уже дана в м2 — просто берём как есть
    if is_ready_m2_item(item):
        return round(float(qty), 1)

    w = item.get("w_mm")
    h = item.get("h_mm")
    d = item.get("d_mm")

    # отвод / переход
    if "отвод" in name or "переход" in name:
        if w is not None and h is not None:
            return calc_elbow_or_transition(w, h)
        return None

    # круглый воздуховод
    if d is not None:
        return calc_round_duct(d, qty)

    # прямоугольный воздуховод
    if w is not None and h is not None:
        return calc_rect_duct(w, h, qty)

    return None


def summarize_by_thickness(items: list[dict]):
    metal_summary = {}

    for item in items:
        if not is_countable_item(item):
            continue

        name = item.get("name", "")
        w = item.get("w_mm")
        h = item.get("h_mm")

        thickness = detect_thickness(name, w, h)
        area = calculate_item(item)

        if thickness is None or area is None:
            continue

        if thickness not in metal_summary:
            metal_summary[thickness] = 0

        metal_summary[thickness] += area

    for t in metal_summary:
        metal_summary[t] = round(metal_summary[t], 1)

    return dict(sorted(metal_summary.items()))