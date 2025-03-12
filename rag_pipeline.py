from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Dict, List, Optional, Tuple
import os
import logging
import random
from config import settings
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from document_loader import DocumentLoader
from sklearn.metrics.pairwise import cosine_similarity

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        """Инициализация RAGPipeline."""
        self.model_name = settings.MODEL_NAME
        self.initialize_model()
        self.initialize_embeddings()
        
        # Создаем директорию для векторной БД
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        
        # Загружаем и дообучаем на эталонных ТЗ
        reference_dir = "references"
        logger.info(f"Проверка папки с эталонными ТЗ: {reference_dir}")
        if os.path.exists(reference_dir) and os.listdir(reference_dir):
            logger.info("Начинаем дообучение эмбеддингов...")
            reference_data = self.load_and_process_reference_tzs(reference_dir)
            texts_for_training = [ref["raw_text"] for ref in reference_data]
            self.train_embeddings_on_references(texts_for_training, "custom_embeddings", epochs=1)
            logger.info("Дообучение завершено, модель сохранена в custom_embeddings")
        else:
            logger.warning("Папка с эталонными ТЗ пуста или не существует, используется базовая модель")

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

    def train_embeddings_on_references(self, reference_data: List[str], output_path: str, epochs: int = 1) -> None:
        """Дообучение эмбеддингов на эталонных ТЗ."""
        model = SentenceTransformer('all-MiniLM-L6-v2')
        train_examples = []
        
        # Фильтруем пустые строки
        valid_texts = [text for text in reference_data if text.strip()]
        if len(valid_texts) < 2:
            logger.warning("Недостаточно данных для дообучения (требуется минимум 2 примера). Пропускаем дообучение.")
            return
        
        # Создаем синтетические пары
        for anchor in valid_texts:
            positive = random.choice([t for t in valid_texts if t != anchor])
            train_examples.append(InputExample(texts=[anchor, positive]))
        
        # Устанавливаем batch_size равным количеству примеров, но минимум 2
        batch_size = max(2, min(len(train_examples), 16))
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
        train_loss = losses.MultipleNegativesRankingLoss(model=model)
        
        logger.info(f"Дообучение на {len(train_examples)} примерах с batch_size={batch_size}...")
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=100,
            output_path=output_path
        )
        logger.info(f"Модель сохранена в {output_path}")
        self.embeddings = HuggingFaceEmbeddings(model_name=output_path)

    def split_tz_into_blocks(self, tz_content: Dict) -> Dict:
        """Разбивает ТЗ на логические блоки."""
        requirements = tz_content['raw_text'].split("\n")
        blocks = {
            "functional": [],
            "non_functional": [],
            "other": []
        }
        
        for req in requirements:
            req = req.strip()
            if not req:
                continue
            if any(keyword in req.lower() for keyword in ["должен", "функция", "реализовать"]):
                blocks["functional"].append(req)
            elif any(keyword in req.lower() for keyword in ["производительность", "безопасность", "надежность"]):
                blocks["non_functional"].append(req)
            else:
                blocks["other"].append(req)
        
        return blocks

    def load_and_process_reference_tzs(self, reference_dir: str) -> List[Dict]:
        """Загружает и обрабатывает эталонные ТЗ из директории."""
        reference_data = []
        loader = DocumentLoader()
        
        for filename in os.listdir(reference_dir):
            file_path = os.path.join(reference_dir, filename)
            content = loader.load_document(file_path)
            if content:
                blocks = self.split_tz_into_blocks({"raw_text": content})
                reference_data.append({
                    "filename": filename,
                    "raw_text": content,
                    "blocks": blocks
                })
                logger.info(f"Загружен эталонный ТЗ: {filename}")
        
        return reference_data

    def process_documents(self, tz_content: Dict, doc_content: Dict) -> Tuple[Chroma, Chroma]:
        """Обработка документов и создание векторного хранилища."""
        try:
            logger.info("Начало обработки документов...")
            if not isinstance(tz_content, dict) or not isinstance(doc_content, dict):
                raise ValueError("Неправильный формат данных: ожидается словарь")
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            tz_chunks = text_splitter.split_text(tz_content['raw_text'])
            doc_chunks = text_splitter.split_text(doc_content['raw_text'])
            
            logger.info(f"Создано чанков: ТЗ - {len(tz_chunks)}, Документация - {len(doc_chunks)}")
            
            tz_vectorstore = Chroma.from_texts(
                texts=tz_chunks, embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "tz")
            )
            doc_vectorstore = Chroma.from_texts(
                texts=doc_chunks, embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "doc")
            )
            
            logger.info("Векторные хранилища успешно созданы")
            return tz_vectorstore, doc_vectorstore
        except Exception as e:
            logger.error(f"Ошибка при обработке документов: {str(e)}")
            raise

    def analyze_documents(self, tz_vectorstore: Chroma, doc_vectorstore: Chroma, tz_content: Dict) -> List[Dict]:
        """Анализ документов и поиск несоответствий."""
        try:
            logger.info("Начало анализа документов...")
            analysis_prompt = PromptTemplate(
                template="""You are an expert in analyzing technical documentation...
                # Оставляем промпт как есть или адаптируем под ваши нужды
                """,
                input_variables=["requirement", "tz_context", "doc_context"]
            )
            
            tz_qa = RetrievalQA.from_chain_type(
                llm=self.llm, chain_type="stuff", retriever=tz_vectorstore.as_retriever(search_kwargs={"k": 3})
            )
            doc_qa = RetrievalQA.from_chain_type(
                llm=self.llm, chain_type="stuff", retriever=doc_vectorstore.as_retriever(search_kwargs={"k": 3})
            )
            
            analysis_results = []
            total_requirements = len(tz_content['requirements'])
            
            for idx, requirement in enumerate(tz_content['requirements'], 1):
                logger.info(f"Анализ требования {idx}/{total_requirements}")
                tz_context = tz_qa.run(requirement)
                doc_context = doc_qa.run(requirement)
                analysis = self.llm.invoke(
                    analysis_prompt.format(requirement=requirement, tz_context=tz_context, doc_context=doc_context)
                ).content
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
        """Определение статуса соответствия и критичности несоответствий."""
        return {"status": "unknown", "criticality": "low"}

    def check_tz_correctness(self, tz_vectorstore: Chroma, reference_data: List[Dict]) -> Dict:
        """Проверяет корректность ТЗ по сравнению с эталонами."""
        tz_text = tz_vectorstore._collection.peek(1)[0]['page_content']
        tz_vector = self.embeddings.embed_documents([tz_text])[0]
        similarities = []
        
        for ref in reference_data:
            ref_vector = self.embeddings.embed_documents([ref["raw_text"]])[0]
            similarity = cosine_similarity([tz_vector], [ref_vector])[0][0]
            similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        return {
            "correctness_score": avg_similarity,
            "is_correct": avg_similarity >= 0.8,
            "comment": "ТЗ корректно" if avg_similarity >= 0.8 else "ТЗ отклоняется от эталона"
        }

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
        explanation_prompt = """You are an expert helping to understand technical requirements...
        # Оставляем промпт как есть или адаптируем
        """
        explanation = rag_pipeline.llm.invoke(explanation_prompt.format(point=point)).content
        return explanation
    except Exception as e:
        logger.error(f"Ошибка при объяснении пункта: {str(e)}")
        raise