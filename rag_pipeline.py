from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Dict, List, Tuple
import os
import logging
from config import settings
import shutil
import re
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Промпты
tz_extraction_prompt = PromptTemplate(
    input_variables=["text"],
    template="Это технический документ:\n\n{text}\n\nИзвлеки ТОЛЬКО конкретные требования из этого документа. Для каждого требования:\n1. Определи суть требования\n2. Преобразуй в краткую и четкую формулировку\n3. Игнорируй пояснительную информацию, примеры и комментарии\n4. Оставь только обязательные характеристики системы\n\nКаждый пункт начинай с '- ' и используй глагол 'должен'."
)

comparison_prompt = PromptTemplate(
    input_variables=["requirements", "doc_content"],
    template="""Вы - эксперт по анализу технической документации. Ваша задача - сравнить требования из ТЗ с содержимым документации и выдать структурированный отчёт.

Инструкции:
1. Рассмотри ВСЕ требования из списка, даже если их много.
2. Для каждого требования проверь, есть ли его подтверждение в документации.
3. Если требование не упоминается, укажи это как причину несоответствия.
4. Не повторяй требования в отчёте — каждое должно быть упомянуто ровно один раз.
5. Ответ должен быть строго в формате:
   - Требование: [текст требования]
   - Соответствует: [да/нет]
   - Причина: [причина, если не соответствует]
Теперь сравни:
Требования:
{requirements}
Документация:
{doc_content}

Ответ: """
)

class RAGPipeline:
    # Список ключей и индекс текущего ключа
    API_KEYS = settings.GROQ_API_KEY.split(",")  # Берем из settings, разделяем по запятой
    current_key_index = 0

    def __init__(self):
        """Инициализация RAGPipeline."""
        self.model_name = settings.MODEL_NAME
        logger.info(f"Используемая модель: {self.model_name}")
        logger.info(f"Токен GROQ_API_KEY: {'установлен' if settings.GROQ_API_KEY else 'не установлен'}")
        self.initialize_model()
        self.initialize_embeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=300,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

    def initialize_model(self) -> None:
        """Инициализация модели через Groq API."""
        try:
            logger.info(f"Инициализация модели {self.model_name} через Groq с ключом {self.current_key_index}...")
            self.llm = ChatGroq(
                groq_api_key=self.API_KEYS[self.current_key_index].strip(),  # Первый ключ из списка, убираем пробелы
                model_name=self.model_name,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )
            logger.info(f"Модель {self.model_name} успешно инициализирована!")
        except Exception as e:
            logger.error(f"Ошибка при инициализации модели: {str(e)}")
            raise

    def switch_api_key(self) -> None:
        """Переключение на следующий API ключ."""
        try:
            self.current_key_index = (self.current_key_index + 1) % len(self.API_KEYS)
            logger.info(f"Переключение на ключ {self.current_key_index}")
            self.llm = ChatGroq(
                groq_api_key=self.API_KEYS[self.current_key_index].strip(),  # Убираем лишние пробелы
                model_name=self.model_name,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )
            logger.info(f"Успешно переключено на ключ {self.current_key_index}")
        except Exception as e:
            logger.error(f"Ошибка при переключении ключа: {str(e)}")
            raise

    def initialize_embeddings(self) -> None:
        """Инициализация эмбеддингов."""
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Эмбеддинги успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации эмбеддингов: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов."""
        text = re.sub(r'\s+', ' ', text)  # Удаляем лишние пробелы
        text = re.sub(r'[^\w\s.,-]', '', text)  # Удаляем специальные символы, кроме точек, запятых и дефисов
        text = text.strip()
        return text

    def split_into_chunks(self, text: str, source: str) -> List[Dict]:
        """Разбивает текст на чанки с метаданными."""
        cleaned_text = self.clean_text(text)
        chunks = self.text_splitter.split_text(cleaned_text)
        return [{"content": chunk, "metadata": {"source": source, "chunk_id": i+1}} for i, chunk in enumerate(chunks)]

    def process_documents(self, tz_content: Dict, doc_content: Dict) -> Tuple[FAISS, FAISS]:
        """Обработка документов и создание векторного хранилища с FAISS."""
        try:
            logger.info("Начало обработки документов...")
            if not isinstance(tz_content, dict) or not isinstance(doc_content, dict):
                raise ValueError("Неправильный формат данных: ожидается словарь")
            
            tz_chunks = self.split_into_chunks(tz_content['raw_text'], "tz")
            doc_chunks = self.split_into_chunks(doc_content['raw_text'], "doc")
            
            logger.info(f"Создано чанков: ТЗ - {len(tz_chunks)}, Документация - {len(doc_chunks)}")
            
            tz_faiss_path = os.path.join(settings.VECTOR_DB_PATH, "tz_faiss")
            doc_faiss_path = os.path.join(settings.VECTOR_DB_PATH, "doc_faiss")

            if os.path.exists(tz_faiss_path):
                shutil.rmtree(tz_faiss_path)
                logger.info("Удалён старый индекс FAISS для ТЗ")
            if os.path.exists(doc_faiss_path):
                shutil.rmtree(doc_faiss_path)
                logger.info("Удалён старый индекс FAISS для документации")

            tz_vectorstore = FAISS.from_texts(
                texts=[chunk["content"] for chunk in tz_chunks],
                embedding=self.embeddings,
                metadatas=[chunk["metadata"] for chunk in tz_chunks]
            )
            tz_vectorstore.save_local(tz_faiss_path)
            logger.info("Создан и сохранён FAISS индекс для ТЗ")

            doc_vectorstore = FAISS.from_texts(
                texts=[chunk["content"] for chunk in doc_chunks],
                embedding=self.embeddings,
                metadatas=[chunk["metadata"] for chunk in doc_chunks]
            )
            doc_vectorstore.save_local(doc_faiss_path)
            logger.info("Создан и сохранён FAISS индекс для документации")
            
            return tz_vectorstore, doc_vectorstore
        except Exception as e:
            logger.error(f"Ошибка при обработке документов: {str(e)}")
            raise

    def extract_tz_requirements(self, tz_content: Dict) -> str:
        """Извлекает требования из ТЗ с промптом."""
        try:
            logger.info("Извлечение требований из ТЗ...")
            tz_text = tz_content["raw_text"][:10000]
            
            requirements = self.llm.invoke(tz_extraction_prompt.format(text=tz_text)).content
            logger.info(f"Извлечённые требования с помощью LLM:\n{requirements}")
            
            cleaned_requirements = []
            for line in requirements.split("\n"):
                line = line.strip()
                if line.startswith("- ") and len(line[2:].strip()) > 10:
                    cleaned_requirements.append(line[2:].strip())
            
            return "\n".join(f"- {req}" for req in cleaned_requirements)
        except Exception as e:
            if "429" in str(e) or "413" in str(e):  # Обработка 429 и 413
                logger.warning(f"Ошибка {str(e).split()[2] if len(str(e).split()) > 2 else 'неизвестно'}, переключение ключа...")
                self.switch_api_key()
                time.sleep(2)  # Задержка для соблюдения лимитов
                return self.extract_tz_requirements(tz_content)  # Повторная попытка
            logger.error(f"Ошибка при извлечении требований из ТЗ: {str(e)}")
            tz_chunks = self.split_into_chunks(tz_text, "tz")
            fallback_result = "\n".join(f"- {chunk['content']}" for chunk in tz_chunks if "должен" in chunk['content'].lower())
            logger.info(f"Использован fallback в extract_tz_requirements:\n{fallback_result}")
            return fallback_result

    def analyze_documents(self, tz_vectorstore: FAISS, doc_vectorstore: FAISS, tz_content: Dict) -> List[Dict]:
        try:
            logger.info("Начало анализа документов...")
            requirements = self.extract_tz_requirements(tz_content)
            doc_docs = doc_vectorstore.similarity_search("", k=10)
            doc_text = "\n".join(doc.page_content for doc in doc_docs)[:10000]
            
            comparison_result = self.llm.invoke(comparison_prompt.format(
                requirements=requirements,
                doc_content=doc_text
            )).content
            logger.info(f"Результат сравнения от Grok:\n{comparison_result}")

            # Обработка ответа от Grok
            analysis_results = []
            lines = comparison_result.split("\n")
            current_requirement = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("- Требование:"):
                    if current_requirement:
                        analysis_results.append(current_requirement)
                    req_text = line.replace("- Требование:", "").strip()
                    if req_text.startswith("[") and req_text.endswith("]"):
                        req_text = req_text[1:-1]
                    current_requirement = {"requirement": req_text}
                elif line.startswith("- Соответствует:"):
                    status_text = line.replace("- Соответствует:", "").strip()
                    if status_text.startswith("[") and status_text.endswith("]"):
                        status_text = status_text[1:-1]
                    # Изменяем статус на нужный текст
                    status = "соответствует ТЗ" if status_text.lower() == "да" else "не соответствует ТЗ"
                    criticality = "нет" if status == "соответствует ТЗ" else "высокая"
                    current_requirement["status"] = {"status": status, "criticality": criticality}
                elif line.startswith("- Причина:"):
                    reason = line.replace("- Причина:", "").strip()
                    if reason.startswith("[") and reason.endswith("]"):
                        reason = reason[1:-1]
                    current_requirement["analysis"] = reason
            
            if current_requirement:
                analysis_results.append(current_requirement)

            logger.info(f"Итоговый анализ:\n{analysis_results}")
            logger.info("Анализ документов завершен успешно")
            return analysis_results
        except Exception as e:
            if "429" in str(e) or "413" in str(e):  # Обработка 429 и 413
                logger.warning(f"Ошибка {str(e).split()[2] if len(str(e).split()) > 2 else 'неизвестно'}, переключение ключа...")
                self.switch_api_key()
                time.sleep(2)  # Задержка для соблюдения лимитов
                return self.analyze_documents(tz_vectorstore, doc_vectorstore, tz_content)  # Повторная попытка
            logger.error(f"Ошибка при анализе документов: {str(e)}")
            req_blocks = [r.strip()[2:] for r in requirements.split("\n") if r.strip().startswith("- ")]
            doc_blocks = [doc.page_content for doc in doc_vectorstore.similarity_search("", k=10)]
            fallback_result = []
            for req in req_blocks:
                matches = any(req.lower() in doc.lower() for doc in doc_blocks)
                # Используем нужный текст и в fallback
                status = "соответствует ТЗ" if matches else "не соответствует ТЗ"
                criticality = "нет" if matches else "высокая"
                fallback_result.append({
                    "requirement": req,
                    "status": {"status": status, "criticality": criticality},
                    "analysis": "Найдено в документации" if matches else "Не найдено в документации"
                })
            logger.info("Использован fallback в analyze_documents")
            return fallback_result

# Глобальные функции
rag_pipeline = RAGPipeline()

def generate_analysis(tz_content: Dict, doc_content: Dict) -> List[Dict]:
    try:
        tz_vectorstore, doc_vectorstore = rag_pipeline.process_documents(tz_content, doc_content)
        analysis_results = rag_pipeline.analyze_documents(tz_vectorstore, doc_vectorstore, tz_content)
        return analysis_results
    except Exception as e:
        logger.error(f"Ошибка при генерации анализа: {str(e)}")
        raise

def explain_point(point: str) -> str:
    try:
        explanation_prompt = """Перефразируй техническое требование в одно краткое предложение. 
        Используй простой язык без технических терминов. Только итоговую формулировку.

        Примеры:
        Исходное: "Программа должна выводить изображение с зелёной линией или сообщением об ошибке"
        Упрощённое: "Программа показывает путь зелёной линией или ошибку"

        Исходное: "Система должна сохранять данные в базе"
        Упрощённое: "Данные автоматически сохраняются в базе"

        Теперь упрости: {point}"""

        response = rag_pipeline.llm.invoke(
            explanation_prompt.format(point=point),
            temperature=0  # Уменьшаем "творческость" модели
        )

        # Удаляем блок <think> и его содержимое
        explanation = re.sub(r"<think>.*?</think>", "", response.content, flags=re.DOTALL).strip()

        # Постобработка: оставляем только первое предложение
        explanation = explanation.split(".")[0] + "." if "." in explanation else explanation
        return explanation.replace("Упрощённое:", "").strip()

    except Exception as e:
        if "429" in str(e) or "413" in str(e):  # Обработка 429 и 413
            logger.warning(f"Ошибка {str(e).split()[2] if len(str(e).split()) > 2 else 'неизвестно'} в explain_point, переключение ключа...")
            rag_pipeline.switch_api_key()
            time.sleep(2)  # Задержка для соблюдения лимитов
            return explain_point(point)  # Повторная попытка
        logger.error(f"Ошибка объяснения: {str(e)}")
        return f"Суть требования: {point.split('.')[0]}" if "." in point else point