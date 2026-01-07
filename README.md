# Project K
> *Formerly known as Project Jarvis / Aether*

**Project K** is an advanced, locally-hosted AI assistant designed to be a "Second Brain" for your computer. It combines local LLM inference with autonomous web research, system control, and a futuristic voice interface.

![Project K UI](https://via.placeholder.com/800x400?text=Project+K+Interface+Preview)

##  Key Features

- ** Local & Private Intelligence**
  - Powered by **Ollama** (supports Llama 3, Mistral, Gemma, etc.).
  - No data leaves your machine unless you explicitly use web search features.

- ** "Always-On" Voice Interface**
  - **Wake Word**: Just say **"Hey K"** (or "Computer") to activate.
  - **Neural TTS**: High-quality, natural-sounding voice output using Edge TTS.
  - **Fluid Conversation**: Talk naturally without needing to press buttons.

- ** Deep Research Agent**
  - Recursive web research capabilities.
  - Can search the web, scrape content, and synthesize comprehensive reports on complex topics.
  - Usage: *"Research the history of quantum computing"*

- ** RAG (Retrieval Augmented Generation)**
  - **"Chat with your Data"**: Upload documents (PDF, TXT, etc.) to your knowledge base.
  - The assistant remembers context and retrieves relevant information from your files.

- ** System Control**
  - Control your PC directly via chat or voice.
  - **Capabilities**: Set volume, mute/unmute, open applications, take screenshots, and more.

- ** Futuristic UI**
  - Built with **Next.js 14**, **Tailwind CSS**, and **Framer Motion**.
  - Features a dynamic "Orb" visualizer that reacts to speaking and listening states.

##  Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Orchestration**: LangChain
- **Vector DB**: ChromaDB (for RAG/Memory)
- **Search**: DuckDuckGo / Custom Scraper
- **Audio**: Edge TTS

### Frontend
- **Framework**: Next.js (React / TypeScript)
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **State**: React Hooks (Custom Voice Hooks)

## Getting Started

### Prerequisites
- **Python** 3.10+
- **Node.js** 18+
- **Gemini Api Key** Google AI Studio
- **Ollama** installed and running locally.

### Installation

1. **Clone the Repository**
    ```bash
    git clone https://github.com/FileNotFound000/Project-K.git
    cd Project-K
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    # Create virtual environment
    python -m venv .venv
    
    # Activate (Windows)
    .venv\Scripts\activate
    # Activate (Mac/Linux)
    # source .venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**
    ```bash
    cd frontend
    npm install
    ```

### Running the Application

1.  **Start Ollama**
    Ensure Ollama is running and you have a model pulled (default is usually `llama3` or `mistral`).
    ```bash
    ollama serve
    # In another terminal: ollama pull llama3
    ```

2.  **Start Backend Server**
    ```bash
    # From /backend directory
    uvicorn main:app --reload
    ```
    Backend will run at: `http://localhost:8000`

3.  **Start Frontend Client**
    ```bash
    # From /frontend directory
    npm run dev
    ```
    Frontend will run at: `http://localhost:3000`

## 📖 Usage Guide

-   **Voice Mode**: Click the "VOICE OFF" button in the top right to enable Wake Word detection. Say "Hey K" to start talking.
-   **Research**: Start your query with "Research..." to trigger the autonomous agent (e.g., "Research the best gaming monitors in 2024").
-   **System Commands**: Try saying "Open Notepad", "Set volume to 50%", or "Mute audio".
-   **Memory**: Drag and drop text files into the chat to add them to the knowledge base.

## 🗺️ Roadmap & Status
Check [PROJECT_STATUS.md](./PROJECT_STATUS.md) for the latest tracking of features, bugs, and future plans.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
[MIT](LICENSE)
