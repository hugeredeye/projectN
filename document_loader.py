import os
from typing import List, Optional
from PyPDF2 import PdfReader
from docx import Document

class DocumentLoader:
    @staticmethod
    def load_pdf(file_path: str) -> str:
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
            return text

    @staticmethod
    def load_docx(file_path: str) -> str:
        doc = Document(file_path)
        text = ''
        for paragraph in doc.paragraphs:
            text += paragraph.text + '\n'
        return text

    @staticmethod
    def load_txt(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def load_document(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None

        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.pdf':
                return self.load_pdf(file_path)
            elif file_extension == '.docx':
                return self.load_docx(file_path)
            elif file_extension == '.txt':
                return self.load_txt(file_path)
            else:
                return None
        except Exception as e:
            print(f"Error loading document: {str(e)}")
            return None
