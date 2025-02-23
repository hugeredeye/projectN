from typing import Dict, Any
import io
from docx import Document
import PyPDF2
from fastapi import HTTPException

class DocumentLoader:
    @staticmethod
    def read_docx(file_bytes: bytes) -> str:
        try:
            doc = Document(io.BytesIO(file_bytes))
            content = []
            for para in doc.paragraphs:
                if para.text.strip():
                    content.append(para.text)
            return "\n".join(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения DOCX: {str(e)}")

    @staticmethod
    def read_pdf(file_bytes: bytes) -> str:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            content = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    content.append(text)
            return "\n".join(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения PDF: {str(e)}")

    @staticmethod
    def read_txt(file_bytes: bytes) -> str:
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return file_bytes.decode('windows-1251')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Ошибка чтения TXT: {str(e)}")

    @classmethod
    def load_document(cls, file_bytes: bytes, filename: str) -> str:
        if filename.endswith('.docx'):
            return cls.read_docx(file_bytes)
        elif filename.endswith('.pdf'):
            return cls.read_pdf(file_bytes)
        elif filename.endswith('.txt'):
            return cls.read_txt(file_bytes)
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый формат файла")
