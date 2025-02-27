from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Text, 
                       Index, Boolean, JSON, func, text)
from datetime import datetime, timedelta
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/document_analyzer")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Модели
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(50), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), default='uploaded')
    md5_hash = Column(String(32), nullable=True)  # Для проверки дубликатов
    is_deleted = Column(Boolean, default=False)    # Soft delete
    delete_date = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)         # Дополнительные метаданные

    # Отношения
    comparison_sessions_tz = relationship("ComparisonSession", foreign_keys="ComparisonSession.tz_file_id", back_populates="tz_file")
    comparison_sessions_doc = relationship("ComparisonSession", foreign_keys="ComparisonSession.doc_file_id", back_populates="doc_file")

    # Индексы
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
    result = Column(JSON, nullable=True)          # Изменили на JSON для структурированных результатов
    error_message = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)  # Время обработки в секундах
    is_deleted = Column(Boolean, default=False)
    
    # Отношения
    tz_file = relationship("UploadedFile", foreign_keys=[tz_file_id], back_populates="comparison_sessions_tz")
    doc_file = relationship("UploadedFile", foreign_keys=[doc_file_id], back_populates="comparison_sessions_doc")

    # Индексы
    __table_args__ = (
        Index('idx_session_status', status),
        Index('idx_created_at', created_at),
        Index('idx_session_id', session_id),
    )

# Класс для управления базой данных
class DatabaseManager:
    def __init__(self):
        self.engine = engine

    async def cleanup_old_files(self, days: int = 30):
        """Очистка старых файлов"""
        async with AsyncSessionLocal() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Помечаем старые файлы как удаленные
            query = text("""
                UPDATE uploaded_files
                SET is_deleted = true,
                    delete_date = NOW()
                WHERE upload_date < :cutoff_date
                AND is_deleted = false
                AND id NOT IN (
                    SELECT tz_file_id FROM comparison_sessions
                    WHERE created_at >= :cutoff_date
                    UNION
                    SELECT doc_file_id FROM comparison_sessions
                    WHERE created_at >= :cutoff_date
                )
            """)
            await session.execute(query, {"cutoff_date": cutoff_date})
            await session.commit()

    async def get_storage_stats(self):
        """Получение статистики хранилища"""
        async with AsyncSessionLocal() as session:
            query = text("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size,
                    AVG(file_size) as avg_size,
                    COUNT(CASE WHEN is_deleted = true THEN 1 END) as deleted_files,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_files
                FROM uploaded_files
            """)
            result = await session.execute(query)
            return dict(result.fetchone())

    async def get_comparison_stats(self):
        """Получение статистики сравнений"""
        async with AsyncSessionLocal() as session:
            query = text("""
                SELECT 
                    COUNT(*) as total_comparisons,
                    AVG(processing_time) as avg_processing_time,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_comparisons,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_comparisons
                FROM comparison_sessions
            """)
            result = await session.execute(query)
            return dict(result.fetchone())

# Dependency для FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Создаем экземпляр менеджера базы данных
db_manager = DatabaseManager() 