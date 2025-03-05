import os
import time
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from document_loader import DocumentLoader
from docx import Document
from utils import format_analysis_response
from config import settings
from rag_pipeline import generate_analysis, explain_point
from database import get_db, UploadedFile, ComparisonSession, db_manager, AsyncSessionLocal, create_tables, engine
from sqlalchemy import select
import uuid
import json
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
from datetime import datetime, timedelta
from tasks import cleanup_task, calculate_storage_stats
import asyncio

# Настраиваем логгер
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Анализ документов")

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


from fastapi.responses import FileResponse


@app.get("/processing")
async def processing_page():
    return FileResponse("static/processing.html")


# Запуск фоновых задач
@app.on_event("startup")
async def startup_event():
    # Создаем таблицы в базе данных
    await create_tables(engine)

    # Запускаем фоновые задачи
    asyncio.create_task(cleanup_task())
    asyncio.create_task(calculate_storage_stats())


# Функция для подсчета MD5 хеша файла
async def calculate_md5(file_path: str) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


# Функция для валидации размера файла
def validate_document_size(file: UploadFile, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    Проверяет, что размер файла не превышает max_size (по умолчанию 10 МБ).
    """
    file.file.seek(0, 2)  # Перемещаем указатель в конец файла
    file_size = file.file.tell()  # Получаем размер файла
    file.file.seek(0)  # Возвращаем указатель в начало файла
    return file_size <= max_size


@app.post("/upload")
async def upload_file(
        file: UploadFile,
        db: AsyncSession = Depends(get_db)
):
    try:
        if not validate_document_size(file):
            raise HTTPException(status_code=413, detail="Размер файла превышает допустимый предел")

        # Генерируем уникальное имя файла
        file_ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_name)

        # Сохраняем файл
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Считаем MD5 хеш
        md5_hash = await calculate_md5(file_path)

        # Проверяем на дубликаты
        query = select(UploadedFile).where(UploadedFile.md5_hash == md5_hash,
                                           UploadedFile.is_deleted == False)
        result = await db.execute(query)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            os.remove(file_path)  # Удаляем дубликат
            return {
                "status": "success",
                "file_id": existing_file.id,
                "filename": existing_file.original_name,
                "message": "Файл уже существует в системе"
            }

        # Сохраняем в базу
        db_file = UploadedFile(
            original_name=file.filename,
            stored_name=stored_name,
            file_type=file.content_type,
            file_size=len(content),
            md5_hash=md5_hash,
            upload_date=datetime.utcnow(),  # Добавляем текущую дату и время
            file_metadata={
                "upload_ip": "user_ip",  # Можно добавить реальный IP
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


@app.post("/compare")
async def compare_documents(
        background_tasks: BackgroundTasks,
        tz_file: UploadFile = File(...),
        project_file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    try:
        start_time = datetime.utcnow()
        session_id = str(uuid.uuid4())

        # Сохраняем файлы
        tz_result = await upload_file(tz_file, db)
        doc_result = await upload_file(project_file, db)

        # Создаем сессию сравнения
        comparison_session = ComparisonSession(
            session_id=session_id,
            tz_file_id=tz_result["file_id"],
            doc_file_id=doc_result["file_id"],
            created_at=start_time
        )
        db.add(comparison_session)
        await db.commit()

        # Запускаем обработку в фоне
        background_tasks.add_task(
            process_documents_task,
            session_id,
            tz_result["file_id"],
            doc_result["file_id"],
            start_time
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


@app.get("/status/{session_id}")
async def get_status(
        session_id: str,
        db: AsyncSession = Depends(get_db)
):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        return {
            "status": session.status,
            "created_at": session.created_at,
            "completed_at": session.completed_at,
            "processing_time": session.processing_time,
            "result": session.result,
            "error_message": session.error_message
        }

    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/stats")
async def get_stats():
    """Получение общей статистики системы"""
    try:
        storage_stats = await db_manager.get_storage_stats()
        comparison_stats = await db_manager.get_comparison_stats()

        return {
            "storage": storage_stats,
            "comparisons": comparison_stats
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/files/{file_id}")
async def delete_file(
        file_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Soft delete файла"""
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


async def process_documents_task(session_id: str, tz_file_id: int, doc_file_id: int, start_time: datetime):
    """Фоновая задача для обработки документов"""
    async with AsyncSessionLocal() as db:
        try:
            # Получаем файлы
            tz_query = select(UploadedFile).where(UploadedFile.id == tz_file_id)
            doc_query = select(UploadedFile).where(UploadedFile.id == doc_file_id)

            tz_result = await db.execute(tz_query)
            doc_result = await db.execute(doc_query)

            tz_file = tz_result.scalar_one_or_none()
            doc_file = doc_result.scalar_one_or_none()

            if not tz_file or not doc_file:
                raise Exception("Файлы не найдены")

            # Пути к файлам
            tz_path = os.path.join(UPLOAD_DIR, tz_file.stored_name)
            doc_path = os.path.join(UPLOAD_DIR, doc_file.stored_name)

            # Читаем содержимое файлов
            def read_file_content(file_path: str) -> Dict:
                """Чтение содержимого файла и преобразование в формат для анализа."""
                try:
                    logger.info(f"Чтение файла: {file_path}")

                    if file_path.endswith(".docx"):
                        # Чтение .docx файла
                        doc = Document(file_path)
                        content = "\n".join([para.text for para in doc.paragraphs])
                    else:
                        # Пробуем сначала utf-8, затем cp1251
                        try:
                            with open(file_path, "r", encoding="utf-8") as file:
                                content = file.read()
                        except UnicodeDecodeError:
                            logger.warning(
                                f"Файл {file_path} не может быть прочитан с кодировкой utf-8. Пробуем cp1251.")
                            with open(file_path, "r", encoding="cp1251") as file:
                                content = file.read()

                    return {
                        "raw_text": content,
                        "requirements": content.split("\n")  # Пример: разбиваем текст на строки как требования
                    }
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
                    raise

            tz_content = read_file_content(tz_path)
            doc_content = read_file_content(doc_path)

            # Выполняем анализ
            analysis_result = generate_analysis(tz_content, doc_content)

            # Обновляем результат в БД
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

            # Обновляем статус в случае ошибки
            query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
            result = await db.execute(query)
            session = result.scalar_one_or_none()

            if session:
                session.status = "error"
                session.error_message = str(e)
                await db.commit()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
