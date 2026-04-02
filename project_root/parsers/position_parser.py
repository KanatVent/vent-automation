import re


def parse_positions(lines):
    positions = []

    size_pattern = re.compile(r'\d{2,4}[xх×]\d{2,4}')
    thickness_pattern = re.compile(r'[бbδ]=?\s*(\d+[.,]?\d*)\s*мм', re.IGNORECASE)
    qty_pattern = re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*(м2|м²|м\.|м|шт\.|шт|кг)', re.IGNORECASE)

    for line in lines:
        pos = {
            "raw": line,
            "type": "неопределено",
            "size": None,
            "thickness": None,
            "qty": None,
            "unit": None
        }

        size = size_pattern.search(line)
        if size:
            pos["size"] = size.group()

        th = thickness_pattern.search(line)
        if th:
            pos["thickness"] = th.group(1).replace(",", ".")

        qty = qty_pattern.search(line)
        if qty:
            pos["qty"] = float(qty.group(1).replace(",", "."))
            pos["unit"] = qty.group(2)

        l = line.lower()
        if "клапан" in l:
            pos["type"] = "клапан"
        elif "решетка" in l:
            pos["type"] = "решетка"
        elif "люк" in l or "лючок" in l:
            pos["type"] = "лючок"
        elif "креплен" in l:
            pos["type"] = "крепление"
        elif pos["size"]:
            pos["type"] = "размерная_позиция"

        if pos["size"] or pos["qty"] is not None:
            positions.append(pos)

    return positions