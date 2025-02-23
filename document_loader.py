import pypdf
import docx

async def process_document(file):
    if file.filename.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif file.filename.endswith(".docx"):
        return extract_text_from_docx(file)
    else:
        return file.read().decode("utf-8")

def extract_text_from_pdf(file):
    reader = pypdf.PdfReader(file.file)
    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file.file)
    return "\n".join([para.text for para in doc.paragraphs])
