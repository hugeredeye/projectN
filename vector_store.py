import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection(name="documents")

def add_document(text, doc_id):
    collection.add(ids=[doc_id], documents=[text])

def search_similar(text, top_k=3):
    return collection.query(query_texts=[text], n_results=top_k)
