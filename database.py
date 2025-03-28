from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Text,
                        Index, Boolean, JSON, func, text)
from datetime import datetime, timedelta
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к базе данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/document_analyzer")
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# Модели
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    md5_hash = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    delete_date = Column(DateTime, nullable=True)
    upload_date = Column(DateTime, nullable=False)
    status = Column(String(50), default='uploaded')
    file_metadata = Column(JSON, nullable=True)

    comparison_sessions_tz = relationship("ComparisonSession", foreign_keys="ComparisonSession.tz_file_id",
                                          back_populates="tz_file")
    comparison_sessions_doc = relationship("ComparisonSession", foreign_keys="ComparisonSession.doc_file_id",
                                           back_populates="doc_file")

    __table_args__ = (
        Index('idx_upload_date', upload_date),
        Index('idx_file_status', status),
        Index('idx_md5_hash', md5_hash),
        Index('idx_is_deleted', is_deleted),
    )


class ComparisonSession(Base):
    __tablename__ = "comparison_sessions"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    tz_file_id = Column(Integer, ForeignKey('uploaded_files.id'))
    doc_file_id = Column(Integer, ForeignKey('uploaded_files.id'))
    status = Column(String(50), default='processing')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False)
    extended_analysis = Column(JSON, nullable=True)

    tz_file = relationship("UploadedFile", foreign_keys=[tz_file_id], back_populates="comparison_sessions_tz")
    doc_file = relationship("UploadedFile", foreign_keys=[doc_file_id], back_populates="comparison_sessions_doc")

    __table_args__ = (
        Index('idx_session_status', status),
        Index('idx_created_at', created_at),
        Index('idx_session_id', session_id),
    )


# Функция для создания таблиц
async def create_tables(engine: AsyncEngine):
    """Создание всех таблиц в базе данных."""
    try:
        async with engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


# Класс для управления базой данных
class DatabaseManager:
    def __init__(self):
        self.engine = engine

    async def cleanup_old_files(self, days: int = 30):
        """Очистка старых файлов"""
        async with AsyncSessionLocal() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = """
                UPDATE uploaded_files
                SET is_deleted = true,
                    delete_date = :now
                WHERE upload_date < :cutoff_date
                AND is_deleted = false
                AND id NOT IN (
                    SELECT tz_file_id FROM comparison_sessions
                    WHERE created_at >= :cutoff_date
                    UNION
                    SELECT doc_file_id FROM comparison_sessions
                    WHERE created_at >= :cutoff_date
                )
            """
            await session.execute(text(query), {
                "cutoff_date": cutoff_date,
                "now": datetime.utcnow()
            })
            await session.commit()

    async def get_storage_stats(self):
        """Получение статистики хранилища"""
        async with AsyncSessionLocal() as session:
            query = """
                SELECT 
                    COUNT(*) as total_files,
                    COALESCE(SUM(file_size), 0) as total_size,
                    COALESCE(AVG(file_size), 0) as avg_size,
                    COUNT(CASE WHEN is_deleted = true THEN 1 END) as deleted_files,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_files
                FROM uploaded_files
            """
            result = await session.execute(text(query))
            row = result.fetchone()
            return {
                "total_files": row[0],
                "total_size": row[1],
                "avg_size": row[2],
                "deleted_files": row[3],
                "processing_files": row[4]
            }


# Dependency для FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Создаем экземпляр менеджера базы данных
db_manager = DatabaseManager()
