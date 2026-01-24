import os
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from pypdf import PdfReader
from docx import Document
from dotenv import load_dotenv

load_dotenv()

# Initialize ChromaDB
# PersistentClient saves to disk
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Use Gemini for embeddings (requires GEMINI_API_KEY)
google_api_key = os.getenv("GEMINI_API_KEY")
if not google_api_key:
    print("Warning: GEMINI_API_KEY not found. RAG will not work.")
else:
    genai.configure(api_key=google_api_key)

# Custom embedding function using Gemini
class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __call__(self, input: list[str]) -> list[list[float]]:
        # Gemini embedding model: models/embedding-001 or models/text-embedding-004
        model = "models/text-embedding-004" 
        return [
            genai.embed_content(model=model, content=text, task_type="retrieval_document")["embedding"]
            for text in input
        ]

# Create or get collection
# We use a custom embedding function to ensure compatibility with Gemini
embedding_fn = GeminiEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name="jarvis_knowledge",
    embedding_function=embedding_fn
)

def ingest_document(file_path: str, filename: str):
    """Reads a file, chunks it, and stores it in ChromaDB."""
    text = ""
    if filename.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif filename.endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif filename.endswith((".txt", ".md", ".py", ".js", ".ts", ".tsx", ".json", ".css", ".html")):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        return "Unsupported file format."

    # Simple chunking (can be improved)
    chunk_size = 1000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    ids = [f"{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": filename, "chunk_id": i} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    return f"Successfully ingested {filename} with {len(chunks)} chunks."

def retrieve_context(query: str, n_results: int = 3) -> str:
    """Searches the vector DB for relevant context."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if not results["documents"]:
        return ""
    
    # Flatten list of list
    context_list = results["documents"][0]
    return "\n\n".join(context_list)

def clear_knowledge_base():
    """Clears all uploaded documents from the vector store."""
    try:
        chroma_client.delete_collection("jarvis_knowledge")
        # Re-create it immediately
        global collection
        collection = chroma_client.get_or_create_collection(
            name="jarvis_knowledge",
            embedding_function=embedding_fn
        )
        return True
    except Exception as e:
        print(f"Error clearing knowledge base: {e}")
        return False
        return False

def remove_document(filename: str) -> str:
    """Removes all chunks associated with a specific filename."""
    try:
        # Delete using metadata filter
        collection.delete(
            where={"source": filename}
        )
        return f"Successfully removed all memories related to {filename}."
    except Exception as e:
        return f"Error removing document: {e}"
