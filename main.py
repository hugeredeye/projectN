from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from document_loader import process_document
from comparer import compare_documents
from rag_pipeline import generate_analysis

app = FastAPI(title="Document Analysis API")

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в API для анализа документов!"}

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

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode("utf-8")  # Предполагаем, что файл в UTF-8
        
        # Анализируем текст
        analysis = generate_analysis(text)
        
        return JSONResponse(content={
            "filename": file.filename,
            "analysis": analysis
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Ошибка при обработке файла: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
