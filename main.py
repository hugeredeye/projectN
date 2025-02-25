from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List
from document_loader import DocumentLoader
from utils import format_analysis_response, validate_document_size
from config import settings
from rag_pipeline import generate_analysis, explain_point

app = FastAPI(title="Document Analysis API")

# Создаем папку для загруженных файлов, если её нет
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем middleware для установки кодировки
@app.middleware("http")
async def add_charset_middleware(request, call_next):
    response = await call_next(request)
    if isinstance(response, HTMLResponse):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding='utf-8') as f:
        return f.read()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Сохраняем файл
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return JSONResponse({
            "filename": file.filename,
            "status": "success"
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/compare")
async def compare_documents(
    tz_file: UploadFile = File(...),
    project_file: UploadFile = File(...)
):
    try:
        # Сохраняем оба файла
        tz_path = os.path.join(UPLOAD_DIR, tz_file.filename)
        project_path = os.path.join(UPLOAD_DIR, project_file.filename)
        
        with open(tz_path, "wb") as buffer:
            content = await tz_file.read()
            buffer.write(content)
            
        with open(project_path, "wb") as buffer:
            content = await project_file.read()
            buffer.write(content)

        return JSONResponse({
            "tz_file": tz_file.filename,
            "project_file": project_file.filename,
            "status": "success",
            "message": "Файлы успешно загружены и готовы к сравнению"
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/explain")
async def explain_document_point(point: str):
    try:
        explanation = explain_point(point)
        return JSONResponse(content={
            "point": point,
            "explanation": explanation
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
