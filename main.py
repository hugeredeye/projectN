from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from document_loader import DocumentLoader
from utils import format_analysis_response, validate_document_size
from config import settings
from rag_pipeline import generate_analysis, explain_point

app = FastAPI(title="Document Analysis API")

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "API для анализа документов",
        "endpoints": {
            "/compare": "Сравнение ТЗ и проектной документации",
            "/explain": "Получение объяснения по конкретному пункту",
            "/docs": "Документация API (Swagger UI)"
        }
    }

@app.post("/compare")
async def compare_documents(
    tz_file: UploadFile = File(...),
    project_file: UploadFile = File(...)
):
    try:
        # Проверяем размер файлов
        for file in [tz_file, project_file]:
            if not validate_document_size(file.size):
                raise HTTPException(status_code=400, detail="Файл слишком большой")

        # Читаем содержимое файлов
        tz_content = DocumentLoader.load_document(await tz_file.read(), tz_file.filename)
        project_content = DocumentLoader.load_document(await project_file.read(), project_file.filename)
        
        # Анализируем документы
        analysis = generate_analysis(tz_content, project_content)
        
        # Форматируем ответ
        formatted_analysis = format_analysis_response(analysis)
        
        return JSONResponse(content={
            "tz_filename": tz_file.filename,
            "project_filename": project_file.filename,
            "analysis": formatted_analysis
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
