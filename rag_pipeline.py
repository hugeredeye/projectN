from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from typing import Dict, List
import os
import logging
from config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.device = settings.DEVICE
        self.initialize_model()
        self.initialize_embeddings()
        
        # Создаем директорию для векторной БД если её нет
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

    def initialize_model(self):
        """Инициализация языковой модели"""
        try:
            logger.info(f"Загрузка модели {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            # Создаем пайплайн для генерации текста
            text_generation = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=settings.MAX_LENGTH,
                temperature=settings.TEMPERATURE,
                top_p=0.95,
                repetition_penalty=1.15
            )

            self.llm = HuggingFacePipeline(pipeline=text_generation)
            logger.info("Модель успешно загружена!")
        except Exception as e:
            logger.error(f"Ошибка при инициализации модели: {str(e)}")
            raise

    def initialize_embeddings(self):
        """Инициализация эмбеддингов"""
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': self.device}
            )
            logger.info("Эмбеддинги успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации эмбеддингов: {str(e)}")
            raise

    def process_documents(self, tz_content: Dict, doc_content: Dict) -> tuple:
        """Обработка документов и создание векторного хранилища"""
        try:
            logger.info("Начало обработки документов...")
            
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

    def analyze_documents(self, tz_vectorstore, doc_vectorstore, tz_content: Dict) -> List[Dict]:
        """Анализ документов и поиск несоответствий"""
        try:
            logger.info("Начало анализа документов...")

            # Создаем промпт для анализа
            analysis_prompt = PromptTemplate(
                template="""
                Проанализируйте следующее требование из технического задания:
                {requirement}

                Контекст из ТЗ:
                {tz_context}

                Контекст из документации:
                {doc_context}

                Определите:
                1. Соответствует ли реализация требованию (полностью/частично/не соответствует)
                2. Какие конкретно несоответствия или проблемы обнаружены
                3. Что нужно исправить

                Ответ должен быть структурированным и конкретным.
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
                analysis = self.llm(
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

    def _determine_status(self, analysis: str) -> str:
        """Определение статуса соответствия на основе анализа"""
        analysis_lower = analysis.lower()
        if "полностью соответствует" in analysis_lower:
            return "full_match"
        elif "частично соответствует" in analysis_lower:
            return "partial_match"
        else:
            return "no_match"

def explain_point(point: str) -> str:
    """Объяснение конкретного пункта"""
    try:
        explanation_prompt = PromptTemplate(
            template="""
            Объясните следующий пункт технического задания простыми словами:
            {point}

            Объяснение должно быть:
            1. Понятным для неспециалиста
            2. Структурированным
            3. С конкретными примерами, где это возможно
            """,
            input_variables=["point"]
        )

        rag_pipeline = RAGPipeline()
        explanation = rag_pipeline.llm(explanation_prompt.format(point=point))
        return explanation

    except Exception as e:
        logger.error(f"Ошибка при объяснении пункта: {str(e)}")
        raise

# Создаем глобальный экземпляр RAGPipeline
rag_pipeline = RAGPipeline()

def generate_analysis(tz_content: Dict, doc_content: Dict) -> List[Dict]:
    """Генерация анализа документов"""
    try:
        # Обрабатываем документы
        tz_vectorstore, doc_vectorstore = rag_pipeline.process_documents(tz_content, doc_content)
        
        # Анализируем документы
        analysis_results = rag_pipeline.analyze_documents(tz_vectorstore, doc_vectorstore, tz_content)
        
        return analysis_results

    except Exception as e:
        logger.error(f"Ошибка при генерации анализа: {str(e)}")
        raise
