import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from document_loader import DocumentLoader
from config import settings
from rag_pipeline import generate_analysis, explain_point
from database import get_db, UploadedFile, ComparisonSession, db_manager, AsyncSessionLocal, create_tables, engine
from sqlalchemy import select
import uuid
import hashlib
from datetime import datetime
from tasks import cleanup_task, calculate_storage_stats
import asyncio

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Анализ документов")

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/processing")
async def processing_page():
    return FileResponse("static/processing.html")

@app.on_event("startup")
async def startup_event():
    await create_tables(engine)
    asyncio.create_task(cleanup_task())
    asyncio.create_task(calculate_storage_stats())

async def calculate_md5(file_path: str) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def validate_document_size(file: UploadFile, max_size: int = 10 * 1024 * 1024) -> bool:
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    return file_size <= max_size

@app.post("/upload")
async def upload_file(file: UploadFile, db: AsyncSessionLocal = Depends(get_db)):
    try:
        if not validate_document_size(file):
            raise HTTPException(status_code=413, detail="Размер файла превышает допустимый предел")

        file_ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_name)

        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        md5_hash = await calculate_md5(file_path)
        query = select(UploadedFile).where(UploadedFile.md5_hash == md5_hash, UploadedFile.is_deleted == False)
        result = await db.execute(query)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            os.remove(file_path)
            os.remove(file_path)

            existing_file.stored_name = stored_name
            await db.commit()
            await db.refresh(existing_file)
            logger.info(f"Обновлён путь для дубликата: {file_path}, ID: {existing_file.id}")
            return {
                "status": "success",
                "file_id": existing_file.id,
                "filename": existing_file.original_name,
                "message": "Файл уже существует в системе"
            }

        db_file = UploadedFile(
            original_name=file.filename,
            stored_name=stored_name,
            file_type=file.content_type,
            file_size=len(content),
            md5_hash=md5_hash,
            upload_date=datetime.utcnow(),
            file_metadata={
                "upload_ip": "user_ip",
                "mime_type": file.content_type,
                "extension": file_ext
            }
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        return {
            "status": "success",
            "file_id": db_file.id,
            "filename": file.filename,
            "message": "Файл успешно загружен"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

async def read_file_content(file_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
    """Чтение содержимого файла из базы данных по его ID."""
    if os.path.exists(file_path):
            os.remove(file_path)
    raise HTTPException(status_code=400, detail=str(e))

async def read_file_content(file_id: int, db: AsyncSessionLocal = Depends(get_db)) -> Dict:
    query = select(UploadedFile).where(UploadedFile.id == file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path = os.path.join(UPLOAD_DIR, file.stored_name)
    loader = DocumentLoader()

    try:
        content = loader.load_document(file_path)
        if not content:
            raise ValueError("Не удалось извлечь текст из файла")
        
        # Выводим текст в логи (первые 500 символов)
        preview = content[:500] + "..." if len(content) > 500 else content
        logger.info(f"Прочитанный текст из файла {file.original_name} (ID: {file_id}):")
        logger.info(preview)
        
        return {
            "raw_text": content,
            "requirements": content.split("\n")
        }
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении файла: {str(e)}")
    preview = content[:500] + "..." if len(content) > 500 else content
    logger.info(f"Прочитанный текст из файла {file.original_name} (ID: {file_id}): {preview}")

    return {
        "raw_text": content,
        "requirements": content.split("\n")


@app.post("/compare")
async def compare_documents(
        background_tasks: BackgroundTasks,
        tz_file: UploadFile = File(...),
        project_file: UploadFile = File(...),
        db: AsyncSessionLocal = Depends(get_db)
):
    try:
        start_time = datetime.utcnow()
        session_id = str(uuid.uuid4())

        tz_result = await upload_file(tz_file, db)
        doc_result = await upload_file(project_file, db)

        comparison_session = ComparisonSession(
            session_id=session_id,
            tz_file_id=tz_result["file_id"],
            doc_file_id=doc_result["file_id"],
            status="processing",
            created_at=start_time
        )
        db.add(comparison_session)
        await db.commit()

        background_tasks.add_task(
            process_documents_task,
            session_id,
            tz_result["file_id"],
            doc_result["file_id"],
            start_time,
            db
        )

        return {
            "status": "processing",
            "session_id": session_id,
            "message": "Начат процесс анализа"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при сравнении: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

async def process_documents_task(session_id: str, tz_file_id: int, doc_file_id: int, start_time: datetime, db: AsyncSessionLocal):
    try:
        tz_content = await read_file_content(tz_file_id, db)
        doc_content = await read_file_content(doc_file_id, db)
        analysis_result = generate_analysis(tz_content, doc_content)

        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if session:
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds())
            session.status = "completed"
            session.completed_at = end_time
            session.processing_time = processing_time
            session.result = analysis_result
            await db.commit()

        logger.info(f"Анализ документов завершен: {session_id}")
    except Exception as e:
        logger.error(f"Ошибка при анализе документов: {str(e)}")
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if session:
            session.status = "error"
            session.error_message = str(e)
            await db.commit()

@app.get("/status/{session_id}")
async def get_status(session_id: str, db: AsyncSessionLocal = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status == "completed" and session.result:
            # Форматируем отчет
            report = []
            for idx, res in enumerate(session.result, 1):
                # Если результат — просто строка в "requirement", задаём значения по умолчанию
                requirement = res.get("requirement", "Не указано")
                status_dict = res.get("status", {})
                analysis = res.get("analysis", "Анализ отсутствует")
                if isinstance(status_dict, dict):
                    status_value = status_dict.get("status", "неизвестно")
                    criticality_value = status_dict.get("criticality", "неизвестно")
                else:
                    # Если status отсутствует или не словарь, определяем по содержимому requirement
                    status_value = "соответствует ТЗ" if "правильно" in requirement.lower() else "не соответствует ТЗ"
                    criticality_value = "нет" if status_value == "соответствует ТЗ" else "высокая"
                report.append({
                    "№": idx,
                    "Требование": requirement,
                    "Статус": status_value,
                    "Критичность": criticality_value,
                    "Анализ": analysis
                })
        else:
            report = None

        return {
            "status": session.status,
            "created_at": session.created_at,
            "completed_at": session.completed_at,
            "processing_time": session.processing_time,
            "report": report,
            "error_message": session.error_message
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/explain")
async def explain_document_point(point: str):
    try:
        explanation = explain_point(point)
        return JSONResponse(content={"point": point, "explanation": explanation})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def explain_document_point(point: str):
    try:
        explanation = explain_point(point)
        return JSONResponse(content={"point": point, "explanation": explanation})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
async def explain_requirement(requirement: Dict[str, str]):
    try:
        point = requirement.get("requirement")
        if not point:
            raise HTTPException(status_code=400, detail="Требование не указано")
        explanation = explain_point(point)
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Ошибка при пояснении: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-report/{session_id}")
async def download_report(session_id: str, db: AsyncSessionLocal = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Отчет еще не готов")

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30)
        elements.append(Paragraph("Отчет о сравнении документов", title_style))

        for idx, res in enumerate(session.result, 1):
            elements.append(Paragraph(f"Пункт {idx}: {res['requirement']}", styles['Heading2']))
            status_color = colors.green if res['status']['status'] == 'соответствует ТЗ' else colors.red
            status_style = ParagraphStyle('Status', parent=styles['Normal'], textColor=status_color)
            elements.append(Paragraph(f"Статус: {res['status']['status']}", status_style))
            elements.append(Paragraph(f"Критичность: {res['status']['criticality']}", styles['Normal']))
            elements.append(Paragraph("Анализ:", styles['Heading3']))
            elements.append(Paragraph(res['analysis'], styles['Normal']))
            elements.append(Spacer(1, 20))

        doc.build(elements)
        buffer.seek(0)

        logger.info(f"PDF отчет сгенерирован для сессии {session_id}")
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{session_id}.pdf",
                "Content-Type": "application/pdf",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/errors/{session_id}")
async def get_errors(session_id: str, db: AsyncSessionLocal = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Отчет еще не готов")

        errors = [{"requirement": res['requirement'], "status": res['status']['status'], 
                   "criticality": res['status']['criticality'], "analysis": res['analysis']} 
                  for res in session.result]
        return {"errors": errors}
    except Exception as e:
        logger.error(f"Ошибка при получении ошибок: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/stats")
async def get_stats():
    try:
        storage_stats = await db_manager.get_storage_stats()
        comparison_stats = await db_manager.get_comparison_stats()
        return {"storage": storage_stats, "comparisons": comparison_stats}
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_id}")
async def delete_file(file_id: int, db: AsyncSessionLocal = Depends(get_db)):
    try:
        query = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await db.execute(query)
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(status_code=404, detail="Файл не найден")

        file.is_deleted = True
        file.delete_date = datetime.utcnow()
        await db.commit()

        return {"status": "success", "message": "Файл помечен как удаленный"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении файла: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)