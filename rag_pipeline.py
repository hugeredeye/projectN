from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Dict, List, Optional, Tuple
import os
import logging
import random
import re
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
from config import settings
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from document_loader import DocumentLoader
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisResult(BaseModel):
    requirement: str
    status: dict
    analysis: str

class RAGPipeline:
    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.initialize_model()
        self.initialize_embeddings()
        self.requirement_patterns = self._init_requirement_patterns()
        self.similarity_threshold = 0.8

    def _init_requirement_patterns(self) -> Dict:
        return {
            "functional": [
                r"(?:ПО|система|программа|модуль)\s+(?:должн[а-я]+|обеспечивает|реализует|должно)\b",
                r"\b(?:требование|функция|реализовать|предусмотреть)\b.*?:",
                r"\d+\.\d+\.\d+\s+[А-Я].*?(?:должен|должна|должно|требуется)",
                r"^[•*-]\s*(?:Система|ПО)\s+должна",
                r"(?:shall|must)\s+implement",
                r"(?:обязательно|необходимо)\s+соблюдение"
            ],
            "non_functional": [
                r"производительность",
                r"безопасность",
                r"надежность",
                r"отказоустойчивость",
                r"эргономичность",
                r"юзабилити",
                r"масштабируемость",
                r"доступность",
                r"скорость работы",
                r"время отклика",
                r"удобство использования",
                r"совместимость с"
            ],
            "exclusions": [
                r"пример[:\s]+",
                r"например[,:\s]+",
                r"пояснение[:\s]+",
                r"комментарий[:\s]+",
                r"для справки[:\s]+",
                r"в качестве иллюстрации",
                r"дополнительно",
                r"детали реализации",
                r"прочие сведения",
                r"(как|для) информации"
            ]
        }

    def initialize_model(self) -> None:
        try:
            self.llm = ChatGroq(
                groq_api_key=settings.GROQ_API_KEY,
                model_name=self.model_name,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )
            logger.info(f"Модель {self.model_name} инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели: {str(e)}")
            raise

    def initialize_embeddings(self) -> None:
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Эмбеддинги инициализированы")
        except Exception as e:
            logger.error(f"Ошибка инициализации эмбеддингов: {str(e)}")
            raise

    def extract_tz_requirements(self, tz_content: Dict) -> List[str]:
        try:
            tz_text = tz_content["raw_text"]
            for pattern in self.requirement_patterns["exclusions"]:
                tz_text = re.sub(pattern, "", tz_text, flags=re.IGNORECASE)
            structured_reqs = re.findall(r"\d+\.\d+\.?\d*\s+([А-Я].*?)(?=\n\d+\.|\Z)", tz_text, re.DOTALL)
            keyword_pattern = "|".join(self.requirement_patterns["functional"] + self.requirement_patterns["non_functional"])
            keyword_reqs = re.findall(rf"({keyword_pattern}).*?[\.\n]", tz_text, re.IGNORECASE)
            return list(set(structured_reqs + keyword_reqs))
        except Exception as e:
            logger.error(f"Ошибка извлечения: {str(e)}")
            return []

    def analyze_documents(self, tz_content: Dict, doc_content: Dict) -> List[Dict]:
        try:
            requirements = self.extract_tz_requirements(tz_content)
            doc_text = doc_content["raw_text"]
            results = []
            for req in requirements:
                req_embedding = self.embeddings.embed_documents([req])[0]
                doc_embedding = self.embeddings.embed_documents([doc_text])[0]
                similarity = cosine_similarity([req_embedding], [doc_embedding])[0][0]
                status = "соответствует" if similarity >= 0.8 else "не соответствует"
                criticality = self.classify_criticality(req)
                results.append({
                    "requirement": req,
                    "status": {"status": status, "criticality": criticality},
                    "analysis": self._generate_analysis_text(status)
                })
            return results
        except Exception as e:
            logger.error(f"Ошибка анализа: {str(e)}")
            return []

    def _generate_analysis_text(self, status: str) -> str:
        return {
            "соответствует": "Требование полностью соответствует документации",
            "не соответствует": "Требование не найдено в документации"
        }.get(status, "Неизвестный статус")

    def classify_criticality(self, requirement: str) -> str:
        if any(re.search(pattern, requirement, re.IGNORECASE) for pattern in self.requirement_patterns["functional"]):
            return "критическое"
        elif any(re.search(pattern, requirement, re.IGNORECASE) for pattern in self.requirement_patterns["non_functional"]):
            return "некритическое"
        return "незначительное"

rag_pipeline = RAGPipeline()

def generate_analysis(tz_content: Dict, doc_content: Dict) -> List[Dict]:
    try:
        analysis_result = rag_pipeline.analyze_documents(tz_content, doc_content)
        return [result.dict() if isinstance(result, AnalysisResult) else result for result in analysis_result]
    except Exception as e:
        logger.error(f"Ошибка генерации анализа: {str(e)}")
        return [{"error": str(e)}]

def explain_point(point: str) -> str:
    try:
        explanation_prompt = f"Объясни техническое требование: {point}"
        explanation = rag_pipeline.llm.invoke(explanation_prompt).content
        return explanation
    except Exception as e:
        logger.error(f"Ошибка объяснения: {str(e)}")
        return f"Объяснение недоступно: {point}"