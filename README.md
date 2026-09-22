# Synthese

Synthese is a FastAPI-based document Q&A application that lets users upload a PDF, extract text from it, and ask natural-language questions about the document content. It uses local ChromaDB vector storage and the Gemini API to answer grounded questions from retrieved document chunks.

Live demo:
https://synthese-api.onrender.com/static/index.html

## Features

- Upload PDF documents
- Extract text and chunk content for retrieval
- Store embeddings locally with ChromaDB
- Ask questions about the uploaded document
- Stream answer generation with Gemini
- Serve a lightweight front-end from the `/static` folder

## How It Works

The project follows a simple retrieval-augmented generation (RAG) flow:

1. A user uploads a PDF from the front end.
2. The FastAPI backend saves the file in the `tmp/` folder and returns a unique `doc_id`.
3. A background task opens the PDF with PyMuPDF, extracts all text, splits it into chunks, and stores those chunks in ChromaDB with metadata such as `doc_id` and chunk index.
4. When the user asks a question, the backend searches ChromaDB for the most relevant text segment(s) tied to that document.
5. The retrieved context is passed to the Gemini model along with a strict prompt instructing it to answer only from the document text.
6. The system streams the answer back to the browser, while also returning the relevant source snippet(s) used for the response.

This means the model does not rely on a generic memory of the document; it answers from the extracted text that was retrieved specifically for the uploaded PDF.

## Tech Stack

- Python 3.11
- FastAPI
- ChromaDB
- PyMuPDF
- Google GenAI SDK
- SlowAPI for rate limiting
- Vanilla HTML/CSS/JavaScript frontend

## Project Structure

- `main.py` — FastAPI app, upload flow, query flow, Gemini integration
- `static/` — front-end UI files
- `data/chroma/` — persistent vector database storage
- `tmp/` — temporary uploaded PDF files
- `requirements.txt` — Python dependencies
- `Dockerfile` — container setup for deployment
- `.env.example` — sample environment variables

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file from the example and add your Gemini API key:

   ```bash
   copy .env.example .env
   ```

   Then update `.env`:

   ```env
   GEMINI_API_KEY=your_gemini_api_key
   ```

## Run locally

Start the API server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open the UI in a browser:

```text
http://localhost:8000/static/index.html
```

## Docker

Build the image:

```bash
docker build -t synthese .
```

Run the container:

```bash
docker run -p 8000:8000 --env-file .env synthese
```

## API Endpoints

- `GET /health` — health check
- `POST /upload` — upload a PDF and get a document ID
- `POST /query` — ask a question about a previously uploaded document

## Notes

- Uploaded PDFs are processed in the background and stored in the local ChromaDB collection.
- Only PDF files are accepted by the upload endpoint.
- Rate limiting is enabled for upload and query requests.
