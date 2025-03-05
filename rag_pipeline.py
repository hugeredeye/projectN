from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Dict, List, Optional, Tuple
import os
import logging
from config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self):
        """Инициализация RAGPipeline."""
        self.model_name = settings.MODEL_NAME
        self.initialize_model()
        self.initialize_embeddings()

        # Создаем директорию для векторной БД, если её нет
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

    def initialize_model(self) -> None:
        """Инициализация модели через Groq API."""
        try:
            logger.info(f"Инициализация модели {self.model_name} через Groq...")

            self.llm = ChatGroq(
                groq_api_key=settings.GROQ_API_KEY,
                model_name=settings.MODEL_NAME,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )

            logger.info("Модель DeepSeek успешно инициализирована!")
        except Exception as e:
            logger.error(f"Ошибка при инициализации модели: {str(e)}")
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

    def process_documents(self, tz_content: Dict, doc_content: Dict) -> Tuple[Chroma, Chroma]:
        """
        Обработка документов и создание векторного хранилища.

        :param tz_content: Словарь с содержимым ТЗ.
        :param doc_content: Словарь с содержимым документации.
        :return: Кортеж из двух векторных хранилищ (для ТЗ и документации).
        """
        try:
            logger.info("Начало обработки документов...")

            # Проверяем формат входных данных
            if not isinstance(tz_content, dict) or not isinstance(doc_content, dict):
                raise ValueError("Неправильный формат данных: ожидается словарь")

            # Разбиваем текст на чанки
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )

            # Обрабатываем ТЗ и документацию
            tz_chunks = text_splitter.split_text(tz_content['raw_text'])
            doc_chunks = text_splitter.split_text(doc_content['raw_text'])

            logger.info(f"Создано чанков: ТЗ - {len(tz_chunks)}, Документация - {len(doc_chunks)}")

            # Создаем векторные хранилища
            tz_vectorstore = Chroma.from_texts(
                texts=tz_chunks,
                embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "tz")
            )

            doc_vectorstore = Chroma.from_texts(
                texts=doc_chunks,
                embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "doc")
            )

            logger.info("Векторные хранилища успешно созданы")
            return tz_vectorstore, doc_vectorstore

        except Exception as e:
            logger.error(f"Ошибка при обработке документов: {str(e)}")
            raise

    def analyze_documents(self, tz_vectorstore: Chroma, doc_vectorstore: Chroma, tz_content: Dict) -> List[Dict]:
        """
        Анализ документов и поиск несоответствий.

        :param tz_vectorstore: Векторное хранилище для ТЗ.
        :param doc_vectorstore: Векторное хранилище для документации.
        :param tz_content: Словарь с содержимым ТЗ.
        :return: Список результатов анализа.
        """
        try:
            logger.info("Начало анализа документов...")

            # Создаем промпт для анализа
            analysis_prompt = PromptTemplate(
                template="""You are an expert in analyzing technical documentation. Your task is to compare the requirement from the technical specification with the implementation in the project documentation.

                ## Requirement from Technical Specification:
                {requirement}

                ## Relevant fragments from Technical Specification:
                {tz_context}

                ## Found fragments in project documentation:
                {doc_context}

                Conduct a detailed analysis and provide a structured response on the following points:

                1. **Compliance Status**: (fully compliant / partially compliant / non-compliant)
                2. **Identified Discrepancies**: (describe each discrepancy in detail)
                3. **Criticality Level**: (critical / major / minor) for each discrepancy
                4. **Required Corrections**: (specific recommendations)
                5. **Assessment Justification**: (why you gave this assessment)

                Important: The analysis should be objective, accurate, and based strictly on the provided document fragments.
                """,
                input_variables=["requirement", "tz_context", "doc_context"]
            )

            # Создаем QA цепочки
            tz_qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=tz_vectorstore.as_retriever(search_kwargs={"k": 3})
            )

            doc_qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=doc_vectorstore.as_retriever(search_kwargs={"k": 3})
            )

            analysis_results = []
            total_requirements = len(tz_content['requirements'])

            for idx, requirement in enumerate(tz_content['requirements'], 1):
                logger.info(f"Анализ требования {idx}/{total_requirements}")

                # Получаем контекст из обоих документов
                tz_context = tz_qa.run(requirement)
                doc_context = doc_qa.run(requirement)

                # Анализируем требование
                analysis = self.llm.predict(
                    analysis_prompt.format(
                        requirement=requirement,
                        tz_context=tz_context,
                        doc_context=doc_context
                    )
                )

                result = {
                    "requirement": requirement,
                    "tz_context": tz_context,
                    "doc_context": doc_context,
                    "analysis": analysis,
                    "status": self._determine_status(analysis)
                }
                analysis_results.append(result)

            logger.info("Анализ документов завершен успешно")
            return analysis_results

        except Exception as e:
            logger.error(f"Ошибка при анализе документов: {str(e)}")
            raise

    def _determine_status(self, analysis: str) -> Dict:
        """
        Определение статуса соответствия и критичности несоответствий.

        :param analysis: Текст анализа.
        :return: Словарь с результатами анализа.
        """
        analysis_lower = analysis.lower()

        # Базовый результат
        result = {
            "status": "unknown",
            "criticality": "unknown",
            "details": {}
        }

        # Определение статуса соответствия
        if "fully compliant" in analysis_lower:
            result["status"] = "full_match"
        elif "partially compliant" in analysis_lower:
            result["status"] = "partial_match"
        elif "non-compliant" in analysis_lower:
            result["status"] = "no_match"

        # Определение уровня критичности
        if "critical" in analysis_lower:
            result["criticality"] = "critical"
        elif "major" in analysis_lower:
            result["criticality"] = "major"
        elif "minor" in analysis_lower:
            result["criticality"] = "minor"

        # Если нет несоответствий, устанавливаем критичность "none"
        if result["status"] == "full_match":
            result["criticality"] = "none"

        # Добавляем детали анализа
        try:
            # Извлекаем несоответствия
            if "identified discrepancies" in analysis_lower:
                inconsistencies_text = analysis.split("Identified Discrepancies")[1].split("Criticality Level")[0]
                result["details"]["inconsistencies"] = inconsistencies_text.strip()

            # Извлекаем необходимые исправления
            if "required corrections" in analysis_lower:
                fixes_text = analysis.split("Required Corrections")[1].split("Assessment Justification")[0]
                result["details"]["fixes"] = fixes_text.strip()
        except Exception:
            # В случае ошибки парсинга, возвращаем только базовый результат
            logger.warning("Не удалось извлечь детали анализа из текста.")

        return result


# Создаем глобальный экземпляр RAGPipeline
rag_pipeline = RAGPipeline()


def generate_analysis(tz_content: Dict, doc_content: Dict) -> List[Dict]:
    """
    Генерация анализа документов.

    :param tz_content: Словарь с содержимым ТЗ.
    :param doc_content: Словарь с содержимым документации.
    :return: Список результатов анализа.
    """
    try:
        # Обрабатываем документы
        tz_vectorstore, doc_vectorstore = rag_pipeline.process_documents(tz_content, doc_content)

        # Анализируем документы
        analysis_results = rag_pipeline.analyze_documents(tz_vectorstore, doc_vectorstore, tz_content)

        return analysis_results

    except Exception as e:
        logger.error(f"Ошибка при генерации анализа: {str(e)}")
        raise


def explain_point(point: str) -> str:
    """
    Объяснение конкретного пункта.

    :param point: Пункт для объяснения.
    :return: Текст объяснения.
    """
    try:
        explanation_prompt = """You are an expert helping to understand technical requirements. Explain the following point from the technical specification:

        {point}

        Provide a detailed explanation that should be:
        1. Understandable for a person without technical education
        2. Well-structured using headings and lists
        3. With specific practical examples
        4. With an explanation of why this point is important for the project

        Avoid professional jargon. If you use technical terms, explain their meaning.
        """

        explanation = rag_pipeline.llm.predict(explanation_prompt.format(point=point))
        return explanation

    except Exception as e:
        logger.error(f"Ошибка при объяснении пункта: {str(e)}")
        raise