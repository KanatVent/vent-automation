from fastapi import FastAPI
from app.routes.web import router as web_router
import uvicorn

app = FastAPI()

app.include_router(web_router)

if __name__ == "__main__":

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
