from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import logging

# Логирование ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Используем модель поменьше для CPU
MODEL_NAME = "facebook/opt-350m"  # Меньшая модель, подходит для CPU

try:
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        use_fast=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,  # Обычная точность для CPU
        device_map="cpu",  # Явно указываем CPU
        low_cpu_mem_usage=True
    )

    logger.info(f"Модель {MODEL_NAME} успешно загружена")

except Exception as e:
    logger.error(f"Ошибка загрузки модели: {str(e)}")
    raise e


def generate_analysis(text: str) -> str:
    """
    Генерация анализа документа с использованием модели deepseek-ai/Janus-Pro-7B.
    
    :param text: Входной текст документа
    :return: Сгенерированный анализ
    """
    try:
        if not text:
            return "Ошибка: входной текст пуст."

        # Ограничение длины текста (примерно под контекст модели)
        max_input_length = 2048
        if len(text) > max_input_length:
            text = text[:max_input_length] + "..."

        # Формируем промпт
        prompt = f"""Task: Analyze the following document in detail. 
        Provide key points, main ideas, and important conclusions.

Document: {text}

Analysis:"""

        # Токенизация
        inputs = tokenizer(prompt, return_tensors="pt")

        # Генерация ответа
        outputs = model.generate(
            **inputs,
            max_length=512,  # Уменьшаем длину для скорости
            temperature=0.7,
            do_sample=True
        )

        # Декодирование результата
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return result

    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        return f"Ошибка анализа: {str(e)}"


# Тестирование модуля
if __name__ == "__main__":
    test_text = """Это тестовый документ для проверки работы модели. 
    Он содержит несколько предложений для анализа."""
    print("\nТестируем генерацию...")
    result = generate_analysis(test_text)
    print("\nРезультат анализа:")
    print(result)
