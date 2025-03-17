import os
from typing import Optional
import textract
import logging
import chardet

logger = logging.getLogger(__name__)

class DocumentLoader:
    def _normalize_line_endings(self, text: str) -> str:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def load_document(self, file_path: str) -> Optional[str]:
        try:
            logger.info(f"Проверка файла: {file_path}")
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            if file_path.lower().endswith('.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из TXT файла: {file_path} (длина: {len(text)})")
                        return text.strip()
                    logger.warning(f"TXT файл пуст: {file_path}")
                    return None
                except UnicodeDecodeError:
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
            
            if file_path.lower().endswith(('.pdf', '.docx', '.doc')):
                try:
                    raw_text = textract.process(file_path, encoding='utf-8', errors='ignore')
                    text = raw_text.decode('utf-8', errors='ignore')
                    if text:
                        text = self._normalize_line_endings(text)
                        logger.info(f"Извлечен текст из файла {file_path} (длина: {len(text)})")
                        return text.strip()
                    logger.warning(f"Файл не содержит текста: {file_path}")
                    return None
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
                    return None
            
            logger.warning(f"Неподдерживаемый формат файла: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
            return None