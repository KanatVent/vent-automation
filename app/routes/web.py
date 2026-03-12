import os
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import UPLOAD_DIR
from app.services.parser_service import parse_pdf
from app.services.storage_service import save_project, load_project
from app.services.calculation_service import calculate_item, summarize_by_thickness

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile):
    path = os.path.join(UPLOAD_DIR, file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    items = parse_pdf(path)
    project_id = save_project(items, file.filename)

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