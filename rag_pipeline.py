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
import re
from config import settings
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from document_loader import DocumentLoader
from sklearn.metrics.pairwise import cosine_similarity

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

requirement_pattern = re.compile(r"[*-]\s*Требование:\s*(.+)$")
status_pattern = re.compile(r"[*-]\s*Соответствует:\s*(.+)$")
reason_pattern = re.compile(r"[*-]\s*Причина:\s*(.+)$")

# Промпты
tz_extraction_prompt = PromptTemplate(
    input_variables=["text"],
    template="Это технический документ:\n\n{text}\n\nИзвлеки ТОЛЬКО конкретные требования из этого документа. Для каждого требования:\n1. Определи суть требования\n2. Преобразуй в краткую и четкую формулировку\n3. Игнорируй пояснительную информацию, примеры и комментарии\n4. Оставь только обязательные характеристики системы\n\nКаждый пункт начинай с '- ' и используй глагол 'должен'."
)

comparison_prompt = PromptTemplate(
    input_variables=["requirements", "doc_content"],
    template="Вот требования к документации:\n\n{requirements}\n\nВот содержимое документации:\n\n{doc_content}\n\nСравни их по блокам и для каждого требования укажи:\n- Требование: [текст]\n- Соответствует: [да/нет]\n- Причина: [текст, если нет]\n"
)

class RAGPipeline:
    def __init__(self):
        """Инициализация RAGPipeline."""
        self.model_name = settings.MODEL_NAME
        logger.info(f"Используемая модель: {self.model_name}")
        logger.info(f"Токен GROQ_API_KEY: {'установлен' if settings.GROQ_API_KEY else 'не установлен'}")
        self.initialize_model()
        self.initialize_embeddings()
        
        # Создаем директорию для векторной БД
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        
        # Инициализация маркеров требований
        self.requirement_patterns = self._init_requirement_patterns()
        
        # Временно отключено обучение на эталонных ТЗ для тестирования
        logger.info("Обучение на эталонных ТЗ временно отключено для тестирования")
        """
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
        """

    def _init_requirement_patterns(self) -> Dict:
        """Инициализация паттернов для определения требований"""
        return {
            "functional": [
                r"(должен|должна|должны|должно)\s+\w+", 
                r"(необходимо|следует|обязан|требуется)\s+\w+",
                r"функция\s+", 
                r"реализовать\s+", 
                r"обеспечить\s+",
                r"предусмотреть\s+",
                r"(система|модуль|компонент|программа|приложение|интерфейс)\s+(должен|должна|должны|должно)\s+",
                r"^\d+\.\d+\s+[А-Я]",  # Нумерованные пункты с заглавной буквы
                r"^[А-Я][а-я]+\s+(должен|должна|должны|должно)\s+",  # Предложения с подлежащим и модальным глаголом
                r"требуется\s+\w+",
                r"должно\s+(быть|иметь|содержать)"
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
        """Инициализация модели через Groq API."""
        try:
            logger.info(f"Инициализация модели {self.model_name} через Groq...")
            self.llm = ChatGroq(
                groq_api_key=settings.GROQ_API_KEY,
                model_name=self.model_name,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )
            logger.info(f"Модель {self.model_name} успешно инициализирована!")
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

    def extract_paragraphs(self, text: str) -> List[str]:
        """Разбивает текст на абзацы с учетом различных разделителей."""
        # Разделяем текст сначала по пустым строкам
        paragraphs = re.split(r'\n\s*\n', text)
        
        result = []
        for p in paragraphs:
            # Проверяем, содержит ли абзац нумерованные пункты
            if re.search(r'^\d+\.', p, re.MULTILINE):
                # Разделяем на пункты
                subparagraphs = re.split(r'(?<=\n)(?=\d+\.)', p)
                result.extend(subparagraphs)
            else:
                result.append(p)
        
        # Очищаем и фильтруем пустые строки
        return [p.strip() for p in result if p.strip()]

    def is_requirement(self, text: str) -> Tuple[bool, str]:
        """Определяет, является ли текст требованием и его тип."""
        text_lower = text.lower()
        
        # Проверяем сначала исключения
        for pattern in self.requirement_patterns["exclusions"]:
            if re.search(pattern, text_lower):
                return False, "non_requirement"
        
        # Проверяем функциональные требования
        for pattern in self.requirement_patterns["functional"]:
            if re.search(pattern, text):
                return True, "functional"
        
        # Проверяем нефункциональные требования
        for pattern in self.requirement_patterns["non_functional"]:
            if re.search(pattern, text_lower):
                return True, "non_functional"
        
        # Эвристики для определения требований без явных маркеров
        # 1. Короткие предложения, начинающиеся с заглавной буквы и заканчивающиеся точкой
        if re.match(r'^[А-Я].*\.$', text) and len(text) < 200:
            # 2. Содержащие глаголы в будущем времени или конкретные указания
            if re.search(r'\s(будет|будут|обеспечивает|поддерживает)\s', text_lower):
                return True, "functional"
            # 3. Предложения с указанием характеристик и параметров
            elif re.search(r'(с точностью|в количестве|в размере|на уровне)', text_lower):
                return True, "non_functional"
                
        return False, "non_requirement"

    def extract_clean_requirement(self, text: str) -> str:
        """Извлекает суть требования, удаляя лишнюю информацию."""
        # Удаляем комментарии в скобках
        text = re.sub(r'\([^)]*\)', '', text)
        # Удаляем вводные фразы
        text = re.sub(r'^В системе |^С учетом |^При разработке |^На этапе ', '', text)
        
        # Если текст слишком длинный, пытаемся выделить основную часть
        if len(text) > 200:
            # Находим первое основное предложение с требованием
            sentences = re.split(r'\.\s+', text)
            for sentence in sentences:
                for pattern in self.requirement_patterns["functional"]:
                    if re.search(pattern, sentence):
                        return sentence.strip() + "."
            
            # Если не нашли конкретное предложение, возвращаем первое предложение
            if sentences:
                return sentences[0].strip() + "."
        
        return text.strip()

    def split_tz_into_blocks(self, tz_content: Dict) -> Dict:
        """Разбивает ТЗ на логические блоки с определением требований."""
        paragraphs = self.extract_paragraphs(tz_content['raw_text'])
        blocks = {
            "functional": [],
            "non_functional": [],
            "other": []
        }
        
        for paragraph in paragraphs:
            is_req, req_type = self.is_requirement(paragraph)
            if is_req:
                if req_type == "functional":
                    blocks["functional"].append(paragraph)
                elif req_type == "non_functional":
                    blocks["non_functional"].append(paragraph)
            else:
                blocks["other"].append(paragraph)
        
        logger.info(f"Разбиение ТЗ: найдено {len(blocks['functional'])} функциональных и "
                   f"{len(blocks['non_functional'])} нефункциональных требований, "
                   f"{len(blocks['other'])} блоков дополнительной информации")
        
        return blocks

    def split_into_blocks(self, text: str) -> List[str]:
        """Разбивает текст на логические блоки."""
        # Сначала разбиваем на абзацы
        paragraphs = self.extract_paragraphs(text)
        
        # Если абзацы слишком большие, дополнительно разбиваем их
        result = []
        for paragraph in paragraphs:
            # Проверяем, является ли абзац требованием
            is_req, _ = self.is_requirement(paragraph)
            
            # Для требований сохраняем целостность независимо от длины
            if is_req:
                result.append(paragraph)
            # Только для нетребований, которые очень длинные, применяем разбиение
            elif len(paragraph) > 2000:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,  # Увеличиваем размер чанка
                    chunk_overlap=100,
                    separators=["\n", ". ", r"(?<=^\d+\.\s+.*$)", " "],
                    length_function=len
                )
                sub_blocks = splitter.split_text(paragraph)
                result.extend(sub_blocks)
            else:
                result.append(paragraph)
        
        return [block.strip() for block in result if block.strip()]

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
            
            # Получаем блоки ТЗ с учетом определения требований
            tz_blocks_dict = self.split_tz_into_blocks(tz_content)
            
            # Объединяем функциональные и нефункциональные требования для векторного хранилища
            tz_blocks = tz_blocks_dict["functional"] + tz_blocks_dict["non_functional"]
            doc_blocks = self.split_into_blocks(doc_content['raw_text'])
            
            logger.info(f"Создано блоков: ТЗ - {len(tz_blocks)}, Документация - {len(doc_blocks)}")
            
            tz_vectorstore = Chroma.from_texts(
                texts=tz_blocks, embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "tz")
            )
            doc_vectorstore = Chroma.from_texts(
                texts=doc_blocks, embedding=self.embeddings,
                persist_directory=os.path.join(settings.VECTOR_DB_PATH, "doc")
            )
            
            logger.info("Векторные хранилища успешно созданы")
            return tz_vectorstore, doc_vectorstore
        except Exception as e:
            logger.error(f"Ошибка при обработке документов: {str(e)}")
            raise

    def extract_tz_requirements(self, tz_content: Dict) -> str:
        """Извлекает требования из ТЗ с промптом."""
        try:
            logger.info("Извлечение требований из ТЗ...")
            tz_text = tz_content["raw_text"][:10000]
            
            # Сначала пробуем извлечь требования с помощью нашей собственной логики
            tz_blocks_dict = self.split_tz_into_blocks({"raw_text": tz_text})
            functional_reqs = [self.extract_clean_requirement(block) for block in tz_blocks_dict["functional"]]
            non_functional_reqs = [self.extract_clean_requirement(block) for block in tz_blocks_dict["non_functional"]]
            
            # Объединяем и удаляем дубликаты
            all_requirements = []
            seen = set()
            
            for req in functional_reqs + non_functional_reqs:
                # Если требования похожи (одно содержится в другом), выбираем более короткое
                is_duplicate = False
                for existing_req in seen:
                    if req in existing_req or existing_req in req:
                        is_duplicate = True
                        break
                
                if not is_duplicate and len(req) > 10:  # Фильтруем слишком короткие
                    all_requirements.append(req)
                    seen.add(req)
            
            # Если наша логика нашла достаточно требований, используем их
            if len(all_requirements) >= 3:
                logger.info(f"Извлечено {len(all_requirements)} требований с помощью логики анализа абзацев")
                requirements = "\n".join(f"- {block}" for block in all_requirements)
                return requirements
            
            # Иначе используем LLM для извлечения требований
            requirements = self.llm.invoke(tz_extraction_prompt.format(text=tz_text)).content
            logger.info(f"Извлечённые требования с помощью LLM:\n{requirements}")
            
            # Постобработка результатов от LLM
            cleaned_requirements = []
            
            for line in requirements.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    # Удаляем '-' и очищаем строку
                    req = line[2:].strip()
                    # Фильтруем пустые и слишком короткие
                    if req and len(req) > 10:
                        cleaned_requirements.append(req)
            
            # Удаляем возможные дубликаты еще раз
            final_requirements = []
            seen = set()
            
            for req in cleaned_requirements:
                req_lower = req.lower()
                if req_lower not in seen:
                    final_requirements.append(req)
                    seen.add(req_lower)
            
            return "\n".join(f"- {req}" for req in final_requirements)
        except Exception as e:
            logger.error(f"Ошибка при извлечении требований из ТЗ: {str(e)}")
            # Fallback: разбиваем на блоки и фильтруем по ключевым словам
            blocks = self.split_into_blocks(tz_text)
            fallback_result = "\n".join(f"- {block}" for block in blocks if any(keyword in block.lower() for keyword in ["требования", "должен", "характеристики"]))
            logger.info(f"Использован fallback в extract_tz_requirements:\n{fallback_result}")
            return fallback_result

    def analyze_documents(self, tz_vectorstore: Chroma, doc_vectorstore: Chroma, tz_content: Dict) -> List[Dict]:
        """Анализ документов и поиск несоответствий."""
        try:
            logger.info("Начало анализа документов...")
            requirements = self.extract_tz_requirements(tz_content)
            doc_text = "\n".join(doc_vectorstore._collection.peek(10)['documents'])[:10000]
            
            try:
                comparison_result = self.llm.invoke(comparison_prompt.format(
                    requirements=requirements,
                    doc_content=doc_text
                )).content
                logger.info(f"Результат сравнения:\n{comparison_result}")
            except Exception as e:
                logger.error(f"Ошибка при вызове LLM для сравнения: {str(e)}")
                # Fallback: сравниваем блоки вручную
                req_blocks = [r.strip()[2:] for r in requirements.split("\n") if r.strip().startswith("- ")]
                doc_blocks = self.split_into_blocks(doc_text)
                fallback_result = []
                for req in req_blocks:
                    matches = any(req.lower() in doc.lower() for doc in doc_blocks)
                    fallback_result.append(
                        f"- Требование: {req}\n"
                        f"- Соответствует: {'да' if matches else 'нет'}\n"
                        f"- Причина: {'Найдено в документации' if matches else 'Не найдено в документации'}"
                    )
                comparison_result = "\n".join(fallback_result)
                logger.info(f"Использован fallback в analyze_documents:\n{comparison_result}")

            analysis_results = []
            lines = comparison_result.split("\n")
            current_requirement = {}
            for line in lines:
                line = line.strip()
                if line.startswith("* Requirement:"):
                    if current_requirement:  # Сохраняем предыдущее требование, если оно есть
                        analysis_results.append(current_requirement)
                    current_requirement = {"requirement": line.replace("* Requirement:", "").strip()}
                elif line.startswith("* Corresponds:"):
                    status_text = line.replace("* Corresponds:", "").strip().lower()
                    # Определяем статус и критичность
                    if "да" in status_text:
                        status = "yes"
                        criticality = "none"
                    elif "частично" in status_text:
                        status = "partial"
                        criticality = "medium"
                    else:
                        status = "no"
                        criticality = "high"
                    current_requirement["status"] = {"status": status, "criticality": criticality}
                elif line.startswith("* Reason:"):
                    reason = line.replace("* Reason:", "").strip()
                    current_requirement["analysis"] = reason

            for line in lines:
                line = line.strip()
                if line.startswith("* Требование:"):
                    if current_requirement:  # Сохраняем предыдущее требование, если оно есть
                        analysis_results.append(current_requirement)
                    current_requirement = {"requirement": line.replace("* Требование:", "").strip()}
                elif line.startswith("* Соответствует:"):
                    status_text = line.replace("* Соответствует:", "").strip().lower()
                    # Определяем статус и критичность
                    if "да" in status_text:
                        status = "yes"
                        criticality = "none"
                    elif "частично" in status_text:
                        status = "partial"
                        criticality = "medium"
                    else:
                        status = "no"
                        criticality = "high"
                    current_requirement["status"] = {"status": status, "criticality": criticality}
                elif line.startswith("* Причина:"):
                    reason = line.replace("* Причина:", "").strip()
                    current_requirement["analysis"] = reason            
                                    
                    # Дополнительная корректировка критичности на основе причины
                    if "status" in current_requirement and current_requirement["status"]["status"] == "no":
                        # Понижаем критичность для несущественных проблем
                        if any(word in reason.lower() for word in ["несущественно", "некритично", "незначительно"]):
                            current_requirement["status"]["criticality"] = "low"
                        # Повышаем критичность для важных проблем
                        elif any(word in reason.lower() for word in ["критично", "важно", "обязательно", "необходимо"]):
                            current_requirement["status"]["criticality"] = "high"
                        else:
                            current_requirement["status"]["criticality"] = "medium"
            
            if current_requirement:
                analysis_results.append(current_requirement)

            logger.info("Анализ документов завершен успешно")
            return analysis_results
        except Exception as e:
            logger.error(f"Ошибка при анализе документов: {str(e)}")
            raise

    def _determine_status(self, analysis: str) -> Dict:
        """Определение статуса соответствия и критичности."""
        analysis_lower = analysis.lower()
        if "выполнено" in analysis_lower or "met" in analysis_lower:
            return {"status": "fulfilled", "criticality": "none"}
        elif "частично" in analysis_lower or "partially" in analysis_lower:
            return {"status": "partially_fulfilled", "criticality": "medium"}
        elif "не выполнено" in analysis_lower or "not met" in analysis_lower:
            return {"status": "not_fulfilled", "criticality": "high"}
        else:
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
        explanation_prompt = """You are an expert helping to understand technical requirements. Explain the following point in simple terms:\n\n{point}"""
        explanation = rag_pipeline.llm.invoke(explanation_prompt.format(point=point)).content
        return explanation
    except Exception as e:
        logger.error(f"Ошибка при объяснении пункта: {str(e)}")
        # Fallback: возвращаем базовое объяснение
        return f"Это требование связано с техническими аспектами: {point}"