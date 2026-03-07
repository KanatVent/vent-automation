import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
PROJECTS_DIR = os.path.join(BASE_DIR, "data", "projects")

DEFAULT_WASTE = 0.10
ELBOW_COEFF = 1.5
TRANSITION_COEFF = 0.6

APP_VERSION = "0.1.0"

for p in [UPLOAD_DIR, EXPORT_DIR, PROJECTS_DIR]:
    os.makedirs(p, exist_ok=True)