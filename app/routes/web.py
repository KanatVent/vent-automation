import os, uuid, json
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services.claude_service import process_pdf
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PROJECTS_DIR = "data/projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs("uploads", exist_ok=True)

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "projects": _load_all_projects()})

@router.post("/calculate", response_class=HTMLResponse)
async def calculate(request: Request, file: UploadFile = File(...), pages: Optional[str] = Form(None)):
    input_path = os.path.join("uploads", file.filename)
    content = await file.read()
    with open(input_path, "wb") as f:
        f.write(content)
    try:
        result = process_pdf(input_path, pages if pages and pages.strip() else None)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e), "projects": _load_all_projects()})
    return templates.TemplateResponse("review.html", {
        "request": request,
        "filename": file.filename,
        "pages": pages or "все",
        "mode": result["mode"],
        "systems": result["systems"],
        "summary": result["summary_by_thickness"],
        "total": result["total_m2"],
        "insulation": result["insulation"],
        "result_json": json.dumps(result, ensure_ascii=False)
    })

@router.post("/save-project")
async def save_project(request: Request):
    body = await request.json()
    project_id = str(uuid.uuid4())
    now = datetime.now()
    project = {
        "id": project_id,
        "filename": body.get("filename", ""),
        "created_at": now.isoformat(),
        "created_date": now.strftime("%d.%m.%Y %H:%M"),
        "status": "waiting_supplier",
        "systems": body.get("systems", []),
        "summary_by_thickness": body.get("summary_by_thickness", {}),
        "total_m2": body.get("total_m2", 0),
        "insulation": body.get("insulation", []),
        "supplier_data": None,
    }
    _save_project(project)
    return JSONResponse({"project_id": project_id})

@router.get("/project/{project_id}", response_class=HTMLResponse)
async def view_project(request: Request, project_id: str):
    project = _load_project(project_id)
    if not project:
        return HTMLResponse("Проект не найден", status_code=404)
    return templates.TemplateResponse("project.html", {"request": request, "project": project})

@router.post("/project/{project_id}/upload-supplier")
async def upload_supplier(request: Request, project_id: str, file: UploadFile = File(...)):
    project = _load_project(project_id)
    if not project:
        return JSONResponse({"error": "Не найден"}, status_code=404)
    supplier_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(supplier_dir, exist_ok=True)
    supplier_path = os.path.join(supplier_dir, file.filename)
    content = await file.read()
    with open(supplier_path, "wb") as f:
        f.write(content)
    try:
        result = process_pdf(supplier_path)
        project["supplier_data"] = {"filename": file.filename, "uploaded_at": datetime.now().isoformat(), "systems": result["systems"]}
        project["status"] = "supplier_received"
        _save_project(project)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"status": "ok"})

def _load_project(pid):
    path = os.path.join(PROJECTS_DIR, f"{pid}.json")
    if not os.path.exists(path): return None
    with open(path, encoding="utf-8") as f: return json.load(f)

def _save_project(p):
    with open(os.path.join(PROJECTS_DIR, f"{p['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)

def _load_all_projects():
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(PROJECTS_DIR, fname), encoding="utf-8") as f:
                    projects.append(json.load(f))
            except: pass
    return sorted(projects, key=lambda x: x.get("created_at",""), reverse=True)
