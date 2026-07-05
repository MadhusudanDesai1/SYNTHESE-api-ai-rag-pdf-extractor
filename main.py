import os
import uuid
import shutil
import json
import fitz  # PyMuPDF
import chromadb
from google import genai
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# --- NEW: SlowAPI Imports ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# Configure the NEW Gemini API Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Ensure temporary upload directory exists
os.makedirs("tmp", exist_ok=True)

# Initialize Database (using local default embeddings)
chroma_client = chromadb.PersistentClient(path="./data/chroma")
collection = chroma_client.get_or_create_collection(name="rag_docs")

# Initialize FastAPI app
app = FastAPI(
    title="Synthese", 
    description="Intelligent document extraction and context synthesis engine.",
    version="1.0.0"
)

# --- NEW: Setup Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class QueryRequest(BaseModel):
    doc_id: str
    question: str

def process_pdf(file_path: str, doc_id: str):
    """Background task to extract, chunk, embed, and store PDF text locally."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        words = text.split()
        chunk_size = 400 
        overlap = 40
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
                
        if not chunks:
            return
        
        ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "chunk_index": i, "text": chunk} for i, chunk in enumerate(chunks)]
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully processed and embedded doc_id: {doc_id}")
        
    except Exception as e:
        print(f"Error processing document {doc_id}: {str(e)}")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/health")
async def health_check():
    """Liveness check endpoint."""
    return {"status": "ok"}

@app.post("/upload", status_code=201)
@limiter.limit("5/minute") # Only allow 5 uploads per minute per user
async def upload_pdf(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload PDF; returns doc_id."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    doc_id = str(uuid.uuid4())
    file_path = f"tmp/{doc_id}.pdf"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(process_pdf, file_path, doc_id)
    
    return {"doc_id": doc_id, "filename": file.filename}

@app.post("/query")
@limiter.limit("10/minute") # Only allow 10 queries per minute per user
async def query_document(request: Request, payload: QueryRequest): # renamed to payload to avoid conflict with Request
    """Query doc; returns generated answer + sources."""
    
    # 1. Retrieve ONLY the single most relevant chunk from ChromaDB
    results = collection.query(
        query_texts=[payload.question],
        n_results=1, # <--- Changed from 3 to 1 to eliminate noise
        where={"doc_id": payload.doc_id}
    )
    
    if not results['documents'] or not results['documents'][0]:
        raise HTTPException(status_code=404, detail="Document not found or no relevant text extracted.")
        
    retrieved_chunks = results['documents'][0]
    
    # 2. Combine chunks into a single context block
    context = "\n\n---\n\n".join(retrieved_chunks)
    
# 3. Build the universally generalized RAG Prompt
    prompt = f"""
    You are a highly precise document extraction engine. 
    Your sole task is to answer the user's question based strictly on the provided context.
    
    CRITICAL INSTRUCTIONS:
    1. RELIANCE: Use ONLY the information present in the 'Retrieved Context'. Do not use prior knowledge.
    2. ABSTENTION: If the context does not contain the exact information needed to answer the question, you must respond with exactly: "I cannot find this information in the document."
    3. PRECISION: Pay close attention to labels, key-value pairs, and adjacent data. Ensure you do not confuse a field's label with a neighboring value.
    4. CONCISENESS: Provide direct, literal answers without unnecessary conversational filler.
    
    Retrieved Context:
    {context}
    
    User Question: {payload.question}
    
    Answer:
    """
    
    # 4. Generator function to yield JSON chunks incrementally
    async def generate_stream():
        yield json.dumps({"sources": retrieved_chunks}) + "\n"
        try:
            response = gemini_client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            for chunk in response:
                if chunk.text:
                    yield json.dumps({"text": chunk.text}) + "\n"
        except Exception as e:
            yield json.dumps({"error": f"LLM Error: {str(e)}"}) + "\n"

    return StreamingResponse(generate_stream(), media_type="application/x-ndjson")