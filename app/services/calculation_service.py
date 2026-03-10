import math
from app.config import DEFAULT_WASTE, ELBOW_COEFF, TRANSITION_COEFF


def to_float(v, default=None):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(str(v).replace(",", "."))
    except ValueError:
        return default


def get_item_length(item: dict) -> float:
    """
    Пока простая логика:
    если unit == 'м', то qty считаем как длину
    иначе длина = 1
    """
    unit = (item.get("unit") or "").lower()
    qty = to_float(item.get("qty"), 1.0)

    if unit == "м":
        return qty or 1.0

    return 1.0


def calculate_rect_duct(item: dict) -> float | None:
    w = to_float(item.get("w_mm"))
    h = to_float(item.get("h_mm"))

    if not w or not h:
        return None

    length_m = get_item_length(item)

    perimeter = ((w / 1000) + (h / 1000)) * 2
    area = perimeter * length_m
    area = area * (1 + DEFAULT_WASTE)

    return round(area, 3)


def calculate_round_duct(item: dict) -> float | None:
    d = to_float(item.get("d_mm"))

    if not d:
        return None

    length_m = get_item_length(item)

    circumference = math.pi * (d / 1000)
    area = circumference * length_m
    area = area * (1 + DEFAULT_WASTE)

    return round(area, 3)


def calculate_elbow(item: dict) -> float | None:
    """
    Пока базовая логика:
    считаем как воздуховод * коэффициент отвода
    """
    if item.get("shape") == "rect":
        base = calculate_rect_duct(item)
    elif item.get("shape") == "round":
        base = calculate_round_duct(item)
    else:
        return None

    if base is None:
        return None

    return round(base * ELBOW_COEFF, 3)


def calculate_transition(item: dict) -> float | None:
    """
    Пока базовая логика:
    считаем как воздуховод * коэффициент перехода
    """
    if item.get("shape") == "rect":
        base = calculate_rect_duct(item)
    elif item.get("shape") == "round":
        base = calculate_round_duct(item)
    else:
        return None

    if base is None:
        return None

    return round(base * TRANSITION_COEFF, 3)


def calculate_insulation(item: dict) -> float | None:
    """
    Пока простая логика для изоляции:
    если unit == м2 → берём qty как площадь
    если unit == м → берём qty как длину
    иначе просто qty
    """
    unit = (item.get("unit") or "").lower()
    qty = to_float(item.get("qty"))

    if qty is None:
        return None

    if unit in ["м2", "m2"]:
        return round(qty, 3)

    if unit in ["м", "m"]:
        return round(qty, 3)

    return round(qty, 3)


def calculate_item(item: dict) -> float | None:
    """
    Главная функция расчёта одной строки
    """
    category = (item.get("category") or "").lower()
    name = (item.get("name") or "").lower()

    if category == "insulation":
        return calculate_insulation(item)

    if "отвод" in name:
        return calculate_elbow(item)

    if "переход" in name:
        return calculate_transition(item)

    if category == "duct":
        if item.get("shape") == "rect":
            return calculate_rect_duct(item)
        if item.get("shape") == "round":
            return calculate_round_duct(item)

    return None


def summarize_by_thickness(items: list[dict]) -> dict:
    summary = {}

    for item in items:
        value = calculate_item(item)
        thickness = item.get("thickness")

        if value is None or thickness is None:
            continue

        summary[thickness] = round(summary.get(thickness, 0) + value, 3)

    return dict(sorted(summary.items()))