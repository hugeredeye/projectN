from fastapi import FastAPI, UploadFile, File
from document_loader import process_document
from comparer import compare_documents
from rag_pipeline import generate_analysis

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в API!"}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    text = await process_document(file)
    return {"text": text}

@app.post("/compare/")
async def compare_files(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    text1 = await process_document(file1)
    text2 = await process_document(file2)
    results = compare_documents(text1, text2)
    return {"comparison": results}

@app.post("/analyze/")
async def analyze_document(file: UploadFile = File(...)):
    text = await process_document(file)
    response = generate_analysis(text)
    return {"analysis": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
