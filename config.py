from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MODEL_NAME: str = "microsoft/phi-2"
    MAX_TOKEN_LENGTH: int = 2048
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    DEVICE: str = "auto"
    SUPPORTED_FORMATS: list = ['.docx', '.pdf', '.txt']

settings = Settings()