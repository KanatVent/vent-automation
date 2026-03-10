import os
import shutil

from fastapi import APIRouter, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import UPLOAD_DIR
from app.services.parser_service import parse_pdf
from app.services.storage_service import save_project, load_project, update_project_items
from app.services.calculation_service import calculate_item, summarize_by_thickness

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Главная страница
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Загрузка PDF
@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile):

    path = os.path.join(UPLOAD_DIR, file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    items = parse_pdf(path)

    project_id = save_project(items, file.filename)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "items": items,
            "project_id": project_id
        }
    )


# Сохранение изменений после review
@router.post("/review/{project_id}", response_class=HTMLResponse)
async def review_save(request: Request, project_id: str):

    form = await request.form()

    row_count = int(form.get("row_count"))

    items = []

    for i in range(row_count):

        if form.get(f"delete_{i}") == "on":
            continue

        def to_int(v):
            try:
                return int(v) if v else None
            except:
                return None

        def to_float(v):
            try:
                return float(str(v).replace(",", ".")) if v else None
            except:
                return None

        item = {
            "page": to_int(form.get(f"page_{i}")),
            "system": form.get(f"system_{i}"),
            "category": form.get(f"category_{i}"),
            "name": form.get(f"name_{i}"),
            "mark": form.get(f"mark_{i}"),
            "shape": form.get(f"shape_{i}"),
            "w_mm": to_int(form.get(f"w_mm_{i}")),
            "h_mm": to_int(form.get(f"h_mm_{i}")),
            "d_mm": to_int(form.get(f"d_mm_{i}")),
            "thickness": to_float(form.get(f"thickness_{i}")),
            "unit": form.get(f"unit_{i}"),
            "qty": to_float(form.get(f"qty_{i}")),
            "raw": form.get(f"raw_{i}")
        }

        items.append(item)

    update_project_items(project_id, items)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "items": items,
            "project_id": project_id,
            "saved": True
        }
    )


# Открытие проекта
@router.get("/project/{project_id}", response_class=HTMLResponse)
async def open_project(request: Request, project_id: str):

    project = load_project(project_id)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "items": project["items"],
            "project_id": project_id
        }
    )


# Расчёт проекта
@router.get("/calculate/{project_id}", response_class=HTMLResponse)
async def calculate_project(request: Request, project_id: str):

    project = load_project(project_id)

    items = project["items"]

    for item in items:
        item["calc_result"] = calculate_item(item)

    summary = summarize_by_thickness(items)

    return templates.TemplateResponse(
        "calc_result.html",
        {
            "request": request,
            "items": items,
            "summary": summary,
            "project_id": project_id
        }
    )