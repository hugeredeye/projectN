import os
from typing import Optional
import textract
import logging

logger = logging.getLogger(__name__)

class DocumentLoader:
    def load_document(self, file_path: str) -> Optional[str]:
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Поддерживаемые форматы: .pdf, .docx, .doc
            if file_path.lower().endswith(('.pdf', '.docx', '.doc')):
                text = textract.process(file_path).decode('utf-8')
                if text:
                    logger.info(f"Извлечен текст из файла: {file_path} (длина: {len(text)})")
                    return text.strip()
                else:
                    logger.warning(f"Не удалось извлечь текст из {file_path}")
                    return None
            else:
                logger.warning(f"Неподдерживаемый формат файла: {file_path}")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
            return None