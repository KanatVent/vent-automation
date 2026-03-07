def parse_pdf(path: str):
    items = [
        {"system": "П1", "raw": "Воздуховод 500x300", "shape": "rect", "w_mm": 500, "h_mm": 300, "d_mm": None, "thickness": 0.7, "qty": 2},
        {"system": "В1", "raw": "Круглый воздуховод Ø250", "shape": "round", "w_mm": None, "h_mm": None, "d_mm": 250, "thickness": 0.5, "qty": 5}
    ]
    return items