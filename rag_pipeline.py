from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import logging
from config import settings

# Логирование ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Используем модель Mistral-7B
try:
    tokenizer = AutoTokenizer.from_pretrained(
        settings.MODEL_NAME,
        use_fast=True,
        trust_remote_code=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        settings.MODEL_NAME,
        torch_dtype=torch.float16,
        device_map=settings.DEVICE,
        trust_remote_code=True
    )

    logger.info(f"Модель {settings.MODEL_NAME} успешно загружена")

except Exception as e:
    logger.error(f"Ошибка загрузки модели: {str(e)}")
    raise e


def generate_analysis(text1, text2):
    """
    Генерация анализа двух документов (ТЗ и проектную документацию) и поиск несоответствий.
    
    :param text1: Текст ТЗ
    :param text2: Текст проектную документацию
    :return: Сгенерированный анализ
    """
    try:
        prompt = f"""Задача: Сравни два документа (ТЗ и проектную документацию) и найди несоответствия.
        Классифицируй каждое несоответствие как критическое, некритическое или незначительное.
        
        ТЗ:
        {text1}

        Проектная документация:
        {text2}

        Формат анализа:
        1. Соответствующие пункты:
        2. Несоответствия:
        3. Пропущенные пункты:
        4. Рекомендации:

        Анализ:"""
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_length=settings.MAX_TOKEN_LENGTH,
            temperature=settings.TEMPERATURE,
            top_p=settings.TOP_P,
            do_sample=True
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        return f"Ошибка анализа: {str(e)}"


def explain_point(point):
    """
    Объяснение конкретного пункта документации.
    
    :param point: Текст пункта документации
    :return: Объяснение пункта
    """
    try:
        prompt = f"""Объясни подробно следующий пункт документации:
        
        {point}
        
        Объяснение:"""
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_length=512,
            temperature=settings.TEMPERATURE
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"Ошибка объяснения: {str(e)}")
        return f"Ошибка объяснения: {str(e)}"


# Тестирование модуля
if __name__ == "__main__":
    test_text1 = """Это тестовый документ для проверки работы модели. 
    Он содержит несколько предложений для анализа."""
    test_text2 = """Это тестовый документ для проверки работы модели. 
    Он содержит несколько предложений для анализа."""
    print("\nТестируем генерацию анализа...")
    result = generate_analysis(test_text1, test_text2)
    print("\nРезультат анализа:")
    print(result)
