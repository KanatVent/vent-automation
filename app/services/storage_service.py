import json
import os
import uuid
from app.config import PROJECTS_DIR, APP_VERSION


def save_project(items: list[dict], source_filename: str) -> str:
    project_id = str(uuid.uuid4())

    payload = {
        "id": project_id,
        "version": APP_VERSION,
        "source_filename": source_filename,
        "items": items
    }

    path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return project_id


def load_project(project_id: str) -> dict:
    path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_project_items(project_id: str, items: list[dict]) -> None:
    path = os.path.join(PROJECTS_DIR, f"{project_id}.json")

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["items"] = items

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)