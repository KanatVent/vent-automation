from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.services.parser_service import parse_pdf
import PyPDF2
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/split", response_class=HTMLResponse)
async def split_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/split")
async def split_pdf(
    request: Request,
    file: UploadFile = File(...),
    pages: str = Form(...)
):
    start, end = map(int, pages.split("-"))

    os.makedirs("uploads", exist_ok=True)
    input_path = os.path.join("uploads", file.filename)

    # читаем файл один раз
    content = await file.read()

    # сохраняем исходный PDF
    with open(input_path, "wb") as f:
        f.write(content)

    # читаем PDF уже с диска
    reader = PyPDF2.PdfReader(input_path)
    writer = PyPDF2.PdfWriter()

    for i in range(start - 1, end):
        writer.add_page(reader.pages[i])

    os.makedirs("exports", exist_ok=True)
    output_path = os.path.join("exports", "result.pdf")

    with open(output_path, "wb") as f:
        writer.write(f)

    items = parse_pdf(input_path)

    print("=== PARSER RESULT ===")
    for item in items[:10]:
        print(item)

    return FileResponse(
        output_path,
        filename="result.pdf",
        media_type="application/pdf"
    )