import os
import shutil
from fastapi import APIRouter, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import UPLOAD_DIR
from app.services.parser_service import parse_pdf

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    items = parse_pdf(path)

    return templates.TemplateResponse("review.html", {"request": request, "items": items})