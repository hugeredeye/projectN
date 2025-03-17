import os
from typing import Optional
import textract
import logging
import chardet

logger = logging.getLogger(__name__)

class DocumentLoader:
    def _normalize_line_endings(self, text: str) -> str:
        """Нормализует переносы строк в тексте."""
        # Заменяем все варианты переносов строк на \n
        text = text.replace('\r\n', '\n')  # Windows
        text = text.replace('\r', '\n')    # Mac
        return text

    def load_document(self, file_path: str) -> Optional[str]:
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Специальная обработка для текстовых файлов
            if file_path.lower().endswith('.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из TXT файла: {file_path} (длина: {len(text)})")
                        return text.strip()
                    else:
                        logger.warning(f"ТXT файл пуст: {file_path}")
                        return None
                except UnicodeDecodeError:
                    # Пробуем другие кодировки, если UTF-8 не работает
                    encodings = ['cp1251', 'latin1', 'iso-8859-5']
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                text = f.read()
                            if text:
                                text = self._normalize_line_endings(text)
                                logger.info(f"Извлечен текст из TXT файла с кодировкой {encoding}: {file_path}")
                                return text.strip()
                        except UnicodeDecodeError:
                            continue
                    logger.error(f"Не удалось прочитать TXT файл с поддерживаемыми кодировками: {file_path}")
                    return None
            
            # Обработка PDF файлов
            if file_path.lower().endswith('.pdf'):
                try:
                    # Пробуем извлечь текст с помощью textract
                    raw_text = textract.process(file_path)
                    
                    # Определяем кодировку извлеченного текста
                    detected = chardet.detect(raw_text)
                    encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                    
                    # Декодируем текст с определенной кодировкой
                    text = raw_text.decode(encoding)
                    
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из PDF файла: {file_path} (длина: {len(text)})")
                        return text.strip()
                    else:
                        logger.warning(f"PDF файл не содержит текста: {file_path}")
                        return None
                except Exception as e:
                    logger.error(f"Ошибка при чтении PDF файла {file_path}: {str(e)}")
                    return None
            
            # Обработка DOCX файлов
            if file_path.lower().endswith('.docx'):
                try:
                    # Пробуем извлечь текст с помощью textract
                    raw_text = textract.process(file_path)
                    
                    # Определяем кодировку извлеченного текста
                    detected = chardet.detect(raw_text)
                    encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                    
                    # Декодируем текст с определенной кодировкой
                    text = raw_text.decode(encoding)
                    
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из DOCX файла: {file_path} (длина: {len(text)})")
                        return text.strip()
                    else:
                        logger.warning(f"DOCX файл не содержит текста: {file_path}")
                        return None
                except Exception as e:
                    logger.error(f"Ошибка при чтении DOCX файла {file_path}: {str(e)}")
                    return None
            
            # Обработка DOC файлов (старый формат)
            if file_path.lower().endswith('.doc'):
                try:
                    # Пробуем извлечь текст с помощью textract
                    raw_text = textract.process(file_path)
                    
                    # Определяем кодировку извлеченного текста
                    detected = chardet.detect(raw_text)
                    encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                    
                    # Декодируем текст с определенной кодировкой
                    text = raw_text.decode(encoding)
                    
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из DOC файла: {file_path} (длина: {len(text)})")
                        return text.strip()
                    else:
                        logger.warning(f"DOC файл не содержит текста: {file_path}")
                        return None
                except Exception as e:
                    logger.error(f"Ошибка при чтении DOC файла {file_path}: {str(e)}")
                    return None
            
            logger.warning(f"Неподдерживаемый формат файла: {file_path}")
            return None
        
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
            return None