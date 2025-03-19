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
    DATABASE_URL: str = "sqlite+aiosqlite:///./document_analyzer.db"  # Значение по умолчанию
    
    # Настройки LLM
    GROQ_API_KEY: str  # Обязательное поле, без значения по умолчанию
    MODEL_NAME: str = "llama3-70b-8192"  # Более вероятная модель для Groq
    MAX_TOKENS: int = 6000
    TEMPERATURE: float = 0.7
    
    # Настройки базы данных векторов
    VECTOR_DB_PATH: str = "vector_db"
    
    class Config:
        case_sensitive = True
        env_file = ".env"  # Автоматическая загрузка из .env
        env_file_encoding = "utf-8"

# Создание экземпляра настроек
settings = Settings()

# Добавьте отладку
print(f"Текущая директория: {os.getcwd()}")
print(f"Найден ли .env: {os.path.exists('.env')}")
print(f"GROQ_API_KEY из окружения: {os.getenv('GROQ_API_KEY')}")
print(f"GROQ_API_KEY из settings: {settings.GROQ_API_KEY}")

if not settings.GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не установлен. Укажите его в переменных окружения или в файле .env")