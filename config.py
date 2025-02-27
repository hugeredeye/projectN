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
    
    # Настройки модели
    MODEL_NAME: str = "microsoft/phi-2"
    DEVICE: str = "cuda" if os.environ.get("USE_GPU", "0") == "1" else "cpu"
    MAX_LENGTH: int = 2048
    TEMPERATURE: float = 0.7
    
    # Настройки базы данных векторов
    VECTOR_DB_PATH: str = "vector_db"
    
    class Config:
        case_sensitive = True

settings = Settings()