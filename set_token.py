import os
import subprocess
from groq import Groq

def setup_groq_token():
    """Настройка токена для доступа к Groq API"""
    print("\n=== Настройка токена Groq API ===")
    print("Для работы требуется токен доступа Groq.")
    print("Токен можно получить на сайте: https://console.groq.com/keys\n")
    
    token = input("Введите ваш токен Groq API: ").strip()
    
    if not token:
        print("Токен не был введён. Отмена настройки.")
        return False
    
    try:
        os.environ["GROQ_API_KEY"] = token
        with open(".env", "w") as f:
            f.write(f"GROQ_API_KEY={token}\n")
        
        try:
            client = Groq(api_key=token)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print("\nТокен успешно настроен! Доступ к модели llama3-70b-8192 подтверждён.")
            return True
        except Exception as e:
            print(f"\nТокен сохранён, но возникла ошибка при проверке: {str(e)}")
            return False
    
    except Exception as e:
        print(f"Ошибка при настройке токена: {str(e)}")
        return False

def run_app_with_token():
    """Запуск приложения с установленным токеном"""
    try:
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        token = line.strip().split("=", 1)[1]
                        os.environ["GROQ_API_KEY"] = token
                        break
        
        print("\nЗапуск приложения с установленным токеном...")
        subprocess.run(["python", "main.py"])
    except Exception as e:
        print(f"Ошибка при запуске приложения: {str(e)}")

# Класс настроек для rag_pipeline
class Settings:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    MODEL_NAME = "llama3-70b-8192"  # Явно задаём правильную модель
    TEMPERATURE = 0
    MAX_TOKENS = 8192
    VECTOR_DB_PATH = "./vector_db"

settings = Settings()

