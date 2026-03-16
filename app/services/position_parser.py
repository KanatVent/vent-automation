import re


def parse_positions(lines):

    positions = []

    size_pattern = re.compile(r'\d{2,4}x\d{2,4}')
    thickness_pattern = re.compile(r'б=(\d+[.,]?\d*)мм')
    qty_pattern = re.compile(r'([0-9]+)\s*(м\.|м|шт\.|шт|кг)')

    for line in lines:

        pos = {
            "raw": line,
            "type": None,
            "size": None,
            "thickness": None,
            "qty": None,
            "unit": None
        }

        l = line.lower()

        if "воздуховод" in l:
            pos["type"] = "воздуховод"

        elif "клапан" in l:
            pos["type"] = "клапан"

        elif "решетка" in l:
            pos["type"] = "решетка"

        elif "люк" in l or "лючок" in l:
            pos["type"] = "лючок"

        elif "креплен" in l:
            pos["type"] = "крепление"

        # размер
        size = size_pattern.search(line)
        if size:
            pos["size"] = size.group()

        # толщина
        th = thickness_pattern.search(line)
        if th:
            pos["thickness"] = th.group(1)

        # количество
        qty = qty_pattern.search(line)
        if qty:
            pos["qty"] = int(qty.group(1))
            pos["unit"] = qty.group(2)

        # если нашли хоть что-то
        if pos["type"] or pos["size"]:
            positions.append(pos)

    return positions