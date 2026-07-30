# Local AI Portfolio Chatbot

## Overview
A production-oriented **local Generative AI chatbot** built with **Streamlit**, **LangChain**, **Ollama**, and **PostgreSQL**.

### Features
- Local LLM inference with Ollama (Phi-3 by default)
- Persistent chat history (PostgreSQL)
- Multiple chat sessions
- Rename chat support
- Adjustable temperature & max tokens
- Dockerized deployment
- LangSmith tracing
- Cached model loading
- Dark UI

## Tech Stack
- Python
- Streamlit
- LangChain
- Ollama
- PostgreSQL
- SQLAlchemy
- Docker

## Project Structure
```text
app.py
helpers.py
postgres/
Dockerfile
docker-compose.yml
requirements.txt
```

## Quick Start
```bash
git clone <repo>
cd <repo>

cp .env.example .env

docker compose up -d
pip install -r requirements.txt
streamlit run app.py
```

## Roadmap
- Streaming responses
- RAG with vector database
- Multi-model support
- Export chats
- Token usage
- Response latency
- Health monitoring
- Authentication
- REST API
- CI/CD
- Unit tests

## License
MIT
