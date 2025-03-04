from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Основные настройки
    PROJECT_NAME: str = "Document Analyzer"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Пути к директориям
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "reports"
    STATIC_DIR: str = "static"
    
    # Настройки файлов
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    
    # Настройки базы данных
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./document_analyzer.db")
    # Настройки LLM
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    MODEL_NAME: str = "deepseek-r1-distill-llama-70b"  # DeepSeek через Groq
    MAX_TOKENS: int = 32768  # Максимальная длина контекста
    TEMPERATURE: float = 0.7
    
    # Настройки базы данных векторов
    VECTOR_DB_PATH: str = "vector_db"
    
    class Config:
        case_sensitive = True

settings = Settings()