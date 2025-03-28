import os
import time
import logging
import re  # Добавляем импорт для работы с регулярными выражениями
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from collections import Counter
from typing import Dict, List
from config import settings
from rag_pipeline import generate_analysis, explain_point, generate_detailed_explanation
from database import get_db, UploadedFile, ComparisonSession, db_manager, AsyncSessionLocal, create_tables, engine
from sqlalchemy import select
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
from datetime import datetime
from tasks import cleanup_task, calculate_storage_stats
import asyncio
from document_loader import DocumentLoader

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Анализ документов")

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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


@app.get("/view-file/{file_id}")
async def view_file(file_id: int, db: AsyncSession = Depends(get_db)):
    """Эндпоинт для просмотра загруженного файла."""
    try:
        query = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await db.execute(query)
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(status_code=404, detail="Файл не найден")

        file_path = os.path.join(UPLOAD_DIR, file.stored_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден на сервере")

        # Определяем тип контента в зависимости от расширения файла
        if file_path.endswith('.pdf'):
            media_type = 'application/pdf'
        elif file_path.endswith('.docx'):
            media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_path.endswith('.txt'):
            media_type = 'text/plain'
        else:
            media_type = 'application/octet-stream'

        return FileResponse(
            file_path,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{file.original_name}"'}
        )
    except Exception as e:
        logger.error(f"Ошибка при просмотре файла: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/file-info/{file_id}")
async def get_file_info(file_id: int, db: AsyncSession = Depends(get_db)):
    """Эндпоинт для получения информации о файле."""
    try:
        query = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await db.execute(query)
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(status_code=404, detail="Файл не найден")

        return {
            "id": file.id,
            "original_name": file.original_name,
            "file_type": file.file_type,
            "file_size": file.file_size,
            "upload_date": file.upload_date,
            "is_deleted": file.is_deleted
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о файле: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
async def upload_file(file: UploadFile, db: AsyncSession = Depends(get_db)):
    try:
        if not validate_document_size(file):
            raise HTTPException(status_code=413, detail="Размер файла превышает допустимый предел")

        file_ext = os.path.splitext(file.filename)[1]
        stored_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_name)

        content = await file.read()
        logger.info(f"Получен файл {file.filename}, размер: {len(content)} байт")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        if not os.path.exists(file_path):
            logger.error(f"Файл не был сохранён: {file_path}")
            raise HTTPException(status_code=500, detail="Не удалось сохранить файл")
        logger.info(f"Файл сохранён: {file_path}, размер: {os.path.getsize(file_path)} байт")

        md5_hash = await calculate_md5(file_path)
        logger.info(f"MD5 хэш файла {file_path}: {md5_hash}")

        query = select(UploadedFile).where(UploadedFile.md5_hash == md5_hash, UploadedFile.is_deleted == False)
        result = await db.execute(query)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            # Обновляем путь к файлу в базе, вместо удаления нового файла
            existing_file.stored_name = stored_name
            await db.commit()
            await db.refresh(existing_file)
            logger.info(f"Обновлён путь для дубликата: {file_path}, ID: {existing_file.id}")
            return {
                "status": "success",
                "file_id": existing_file.id,
                "filename": existing_file.original_name,
                "message": "Файл уже существует, путь обновлён"
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

        logger.info(f"Файл добавлен в базу, ID: {db_file.id}")
        return {
            "status": "success",
            "file_id": db_file.id,
            "filename": file.filename,
            "message": "Файл успешно загружен"
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)  # Удаляем файл, если он был создан, но произошла ошибка
        raise HTTPException(status_code=400, detail=str(e))


async def read_file_content(file_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
    query = select(UploadedFile).where(UploadedFile.id == file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path = os.path.join(UPLOAD_DIR, file.stored_name)
    logger.info(f"Чтение файла: {file_path}, существует: {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        logger.error(f"Файл не найден на диске: {file_path}")
        raise HTTPException(status_code=500, detail=f"Файл не найден на диске: {file_path}")

    loader = DocumentLoader()
    content = loader.load_document(file_path)
    if not content:
        logger.error(f"Не удалось извлечь текст из файла: {file_path}")
        raise ValueError("Не удалось извлечь текст из файла")

    preview = content[:500] + "..." if len(content) > 500 else content
    logger.info(f"Прочитанный текст из файла {file.original_name} (ID: {file_id}):")
    logger.info(preview)

    return {
        "raw_text": content,
        "requirements": content.split("\n")
    }


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


async def process_documents_task(session_id: str, tz_file_id: int, doc_file_id: int, start_time: datetime,
                                 db: AsyncSession):
    try:
        logger.info(f"Начало обработки сессии {session_id}")
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
async def get_status(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status == "completed" and session.result:
            report = []
            for idx, res in enumerate(session.result, 1):
                report.append({
                    "№": idx,
                    "Требование": res["requirement"],
                    "Статус": res["status"]["status"],
                    "Критичность": res["status"]["criticality"],
                    "Анализ": res["analysis"]
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
async def explain_requirement(request: Dict[str, str], db: AsyncSession = Depends(get_db)):
    """Эндпоинт для получения пояснений по конкретному требованию."""
    try:
        requirement = request.get("requirement")
        if not requirement:
            raise HTTPException(status_code=400, detail="Требование не указано")

        # Запрашиваем пояснение через функцию explain_point из rag_pipeline
        explanation = explain_point(requirement)
        logger.info(f"Пояснение для требования '{requirement}': {explanation}")

        return JSONResponse(content={
            "requirement": requirement,
            "explanation": explanation
        })
    except Exception as e:
        logger.error(f"Ошибка при получении пояснения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке запроса: {str(e)}")


@app.post("/find-in-document")
async def find_in_document(request: Dict[str, str], db: AsyncSession = Depends(get_db)):
    """Строгий поиск с проверкой через анализ карточки"""
    try:
        requirement = request.get("requirement")
        session_id = request.get("session_id")

        if not requirement or not session_id:
            raise HTTPException(status_code=400, detail="Не указано требование или ID сессии")

        # Получаем сессию и анализ из карточки
        session = await db.execute(
            select(ComparisonSession)
            .where(ComparisonSession.session_id == session_id)
        )
        session = session.scalar_one_or_none()

        if not session or not session.result:
            raise HTTPException(status_code=404, detail="Сессия или результаты анализа не найдены")

        # Находим соответствующий пункт в анализе
        card_analysis = next(
            (item for item in session.result
             if item["requirement"].lower() == requirement.lower()),
            None
        )

        if not card_analysis:
            return {
                "status": "success",
                "found": False,
                "message": "Требование не найдено в анализе"
            }

        # Если в карточке указано, что требование отсутствует
        if card_analysis["status"]["status"] == "не соответствует ТЗ":
            return {
                "status": "success",
                "found": False,
                "message": card_analysis.get("analysis", "Требование отсутствует в документации")
            }

        # Загружаем оригинальный текст документации
        doc_file = await db.get(UploadedFile, session.doc_file_id)
        doc_content = await read_file_content(doc_file.id, db)
        full_text = doc_content['raw_text'].lower()

        # 1. Строгий поиск точного совпадения
        exact_matches = list(re.finditer(re.escape(requirement.lower()), full_text))

        if exact_matches:
            context = get_match_context(full_text, exact_matches[0])
            cleaned_context = clean_text(context)
            sentences = split_into_sentences(cleaned_context)
            return {
                "status": "success",
                "found": True,
                "match_type": "exact",
                "results": [{
                    "content": sentences,  # Возвращаем список предложений
                    "positions": [[m.start(), m.end()] for m in exact_matches]
                }]
            }

        # 2. Поиск по ключевым словам из анализа
        if "analysis" in card_analysis:
            keywords = extract_keywords(card_analysis["analysis"])
            found_sentences = []

            for sentence in re.split(r'(?<=[.!?])\s+', full_text):
                if any(keyword in sentence for keyword in keywords):
                    cleaned_sentence = clean_text(sentence[:500])
                    if cleaned_sentence:
                        found_sentences.append(cleaned_sentence)

            if found_sentences:
                return {
                    "status": "success",
                    "found": True,
                    "match_type": "keywords",
                    "results": [{
                        "content": found_sentences,  # Возвращаем список предложений
                        "message": "Найдено по ключевым словам из анализа"
                    }]
                }

        # 3. Если ничего не найдено
        return {
            "status": "success",
            "found": False,
            "message": card_analysis.get("analysis", "Требование не найдено в документации")
        }

    except Exception as e:
        logger.error(f"Ошибка поиска: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def get_match_context(text: str, match: re.Match, window: int = 100) -> str:
    """Возвращает контекст вокруг совпадения"""
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return text[start:end]

def clean_text(text: str) -> str:
    """Очищает текст от лишних символов и форматирует ссылки"""
    # Удаляем или заменяем ссылки вида [...].21 4
    text = re.sub(r'\[\.\.\.\]\.\d+\s+\d+\.\d+', '', text)
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_into_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_keywords(text: str) -> List[str]:
    """Извлекает ключевые слова из анализа"""
    words = re.findall(r'\w{4,}', text.lower())  # Слова от 4 символов
    freq = Counter(words)
    return [word for word, count in freq.most_common(5)]  # Топ-5 частых слов


@app.post("/detailed-explain")
async def detailed_explain(
        request: Dict[str, str],
        db: AsyncSession = Depends(get_db)
):
    """Эндпоинт для детального пояснения"""
    try:
        requirement = request["requirement"]
        session_id = request["session_id"]

        # Получаем сессию сравнения
        session = await db.execute(
            select(ComparisonSession)
            .where(ComparisonSession.session_id == session_id)
        )
        session = session.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        # Получаем файлы
        tz_file = await db.get(UploadedFile, session.tz_file_id)
        doc_file = await db.get(UploadedFile, session.doc_file_id)

        # Читаем содержимое
        tz_content = await read_file_content(tz_file.id, db)
        doc_content = await read_file_content(doc_file.id, db)

        # Новое: получаем анализ из существующей карточки
        card_analysis = next(
            (item["analysis"] for item in session.result
             if item["requirement"] == requirement),
            "Анализ не найден"
        )

        explanation = generate_detailed_explanation(
            requirement=requirement,
            tz_content=tz_content,
            doc_content=doc_content,
            card_analysis=card_analysis  # Передаем анализ
        )

        return {"explanation": explanation}

    except Exception as e:
        logger.error(f"Ошибка детального пояснения: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-report/{session_id}")
async def download_report(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Отчет еще не готов")

        # Создаем PDF отчет
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.units import inch
        import io

        # Регистрируем шрифт Times New Roman
        try:
            # Укажите путь к файлу Times New Roman (например, 'static/fonts/times.ttf')
            pdfmetrics.registerFont(TTFont('TimesNewRoman', 'static/fonts/times.ttf'))
        except Exception as e:
            logger.error(f"Ошибка регистрации шрифта: {str(e)}")
            raise HTTPException(status_code=500, detail="Ошибка регистрации шрифта")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            encoding='utf-8'
        )

        styles = getSampleStyleSheet()

        def sanitize_text(text):
            """Подготовка текста для PDF."""
            if not isinstance(text, str):
                return str(text)
            return text

        def create_style(base_style_name, font_size=12, space_after=10, alignment=0):
            return ParagraphStyle(
                name=f'Custom{base_style_name}',
                parent=styles[base_style_name],
                fontName='TimesNewRoman',
                fontSize=font_size,
                spaceAfter=space_after,
                alignment=alignment,
                encoding='utf-8',
                leading=font_size * 1.2
            )

        # Создаем стили
        normal_style = create_style('Normal')
        heading1_style = create_style('Heading1', font_size=24, space_after=30, alignment=1)
        heading2_style = create_style('Heading2', font_size=18, space_after=20)
        heading3_style = create_style('Heading3', font_size=14, space_after=15)

        elements = []

        # Добавляем заголовок
        elements.append(Paragraph(sanitize_text("Отчет о сравнении документов"), heading1_style))
        elements.append(Spacer(1, 30))

        # Добавляем результаты анализа
        for idx, res in enumerate(session.result, 1):
            try:
                # Заголовок пункта
                requirement_text = sanitize_text(f"Пункт {idx}: {res['requirement']}")
                elements.append(Paragraph(requirement_text, heading2_style))

                # Статус и критичность
                status_color = colors.green if res['status']['status'] == 'соответствует ТЗ' else colors.red
                status_style = ParagraphStyle(
                    'Status',
                    parent=normal_style,
                    textColor=status_color,
                    fontName='TimesNewRoman',
                    fontSize=12,
                    spaceAfter=10,
                    encoding='utf-8'
                )

                elements.append(Paragraph(sanitize_text(f"Статус: {res['status']['status']}"), status_style))
                elements.append(Paragraph(sanitize_text(f"Критичность: {res['status']['criticality']}"), normal_style))

                # Анализ
                elements.append(Paragraph(sanitize_text("Анализ:"), heading3_style))
                elements.append(Paragraph(sanitize_text(res['analysis']), normal_style))
                elements.append(Spacer(1, 20))
            except Exception as e:
                logger.error(f"Ошибка при обработке пункта {idx}: {str(e)}")
                continue

        try:
            # Создаем PDF
            doc.build(elements)
            buffer.seek(0)

            logger.info(f"PDF отчет успешно сгенерирован для сессии {session_id}")

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="report_{session_id}.pdf"',
                    "Content-Type": "application/pdf; charset=utf-8",
                    "Cache-Control": "no-cache"
                }
            )
        except Exception as e:
            logger.error(f"Ошибка при создании PDF: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/errors/{session_id}")
async def get_errors(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        query = select(ComparisonSession).where(ComparisonSession.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Отчет еще не готов")

        # Формируем список всех пунктов (соответствия и несоответствия)
        errors = []
        for res in session.result:
            errors.append({
                "requirement": res['requirement'],
                "status": res['status']['status'],
                "criticality": res['status']['criticality'],
                "analysis": res['analysis']
            })

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
async def delete_file(file_id: int, db: AsyncSession = Depends(get_db)):
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
