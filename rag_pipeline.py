from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Используем маленькую модель для начала
MODEL_NAME = "facebook/opt-1.3b"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    legacy=False,
    use_fast=True
)

# Определяем устройство
device = "cuda" if torch.cuda.is_available() else "cpu"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    device_map="auto" if device == "cuda" else None,
    low_cpu_mem_usage=True
)

def generate_analysis(text):
    try:
        # Оптимизированный промпт для лучшего качества анализа
        prompt = f"""Task: Analyze the following document.
Document: {text}
Analysis:"""
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_length=1024,
            temperature=0.7,
            top_p=0.9,  # Nucleus sampling для лучшей генерации
            do_sample=True,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        print(f"Ошибка при генерации анализа: {e}")
        return f"Ошибка анализа: {str(e)}"

# Тестирование
if __name__ == "__main__":
    print(f"Используется устройство: {device}")
    test_text = "Это тестовый документ для проверки работы модели."
    print("Тестируем генерацию...")
    result = generate_analysis(test_text)
    print("\nРезультат анализа:")
    print(result)