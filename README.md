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

## Benchmarking and Impact Measurement

To validate the retrieval quality of the RAG system, I ran a focused evaluation against the project’s actual ChromaDB collection. The benchmark was designed to answer one practical question: how reliably does the vector search retrieve the correct document chunk for a fact-based question from the stored PDFs?

### Evaluation method

- I used the real persisted ChromaDB index in `data/chroma`.
- I created a small benchmark set from factual information already present in the embedded documents, such as project metadata, candidate details, course information, and IELTS-related content.
- For each query, I matched it to a known gold chunk in the same document and then measured whether the expected chunk was returned in the top results.
- Retrieval latency was measured in milliseconds for each query using the same `collection.query()` pipeline the app uses in production.

### Metrics used

- Recall@1: whether the correct chunk appears as the top result.
- Recall@5: whether the correct chunk appears within the top 5 results.
- MRR (Mean Reciprocal Rank): how highly the correct chunk ranks on average.
- Retrieval latency: average, median, min, and max query time in milliseconds.

### Actual benchmark results

These are the measurements captured from the current implementation and saved in `rag_evaluation.txt`:

- Recall@1: 0.875000
- Recall@5: 1.000000
- MRR: 0.937500
- Average latency: 55.0126 ms
- Median latency: 28.9955 ms
- Min latency: 26.7184 ms
- Max latency: 239.5343 ms

### Why this matters

This benchmark quantifies the practical impact of the project in a measurable way:

- The retrieval layer is highly effective for the tested factual queries because Recall@5 is 1.0.
- The system also ranks the correct chunk very well on average, reflected by an MRR of 0.9375.
- Retrieval remains fast enough for interactive use, with median latency under 29 ms and average latency around 55 ms.

The benchmark script used for this evaluation is `rag_benchmark.py`, and the full output is stored in `rag_evaluation.txt`.

## Notes

- Uploaded PDFs are processed in the background and stored in the local ChromaDB collection.
- Only PDF files are accepted by the upload endpoint.
- Rate limiting is enabled for upload and query requests.
