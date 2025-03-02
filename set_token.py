import os
import logging
import subprocess
from groq import Groq

def setup_groq_token():
    """Настройка токена для доступа к Groq API"""
    print("\n=== Настройка токена Groq API ===")
    print("Для использования DeepSeek-R1 требуется токен доступа Groq.")
    print("Токен можно получить на сайте: https://console.groq.com/keys\n")
    
    token = input("Введите ваш токен Groq API: ").strip()
    
    if not token:
        print("Токен не был введен. Отмена настройки.")
        return False
    
    try:
        # Устанавливаем токен как переменную окружения
        os.environ["GROQ_API_KEY"] = token
        
        # Сохраняем токен в файл для загрузки в будущем
        with open(".env", "w") as f:
            f.write(f"GROQ_API_KEY={token}\n")
        
        # Проверяем доступ к API
        try:
            client = Groq(api_key=token)
            # Пробуем выполнить простой запрос для проверки токена
            response = client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print("\nТокен успешно настроен! У вас есть доступ к модели deepseek-r1-distill-llama-70b.")
            return True
        except Exception as e:
            print(f"\nТокен сохранен, но возникла ошибка при проверке доступа: {str(e)}")
            return False
    
    except Exception as e:
        print(f"Ошибка при настройке токена: {str(e)}")
        return False

def run_app_with_token():
    """Запуск приложения с установленным токеном"""
    try:
        # Загружаем токен из .env файла
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        token = line.strip().split("=", 1)[1]
                        os.environ["GROQ_API_KEY"] = token
                        break
        
        # Запускаем основное приложение
        print("\nЗапуск приложения с установленным токеном...")
        subprocess.run(["python", "main.py"])
        
    except Exception as e:
        print(f"Ошибка при запуске приложения: {str(e)}")

if __name__ == "__main__":
    if os.environ.get("GROQ_API_KEY"):
        print("Токен GROQ_API_KEY уже установлен в переменных окружения.")
        run_app = input("Запустить приложение? (y/n): ").lower()
        if run_app == 'y':
            run_app_with_token()
    else:
        if setup_groq_token():
            run_app = input("Запустить приложение? (y/n): ").lower()
            if run_app == 'y':
                run_app_with_token()