# 🎬 Movie Agent

An AI-powered movie assistant that answers natural-language questions about films and TV shows using real-time data from the OMDb API.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────┐        ┌─────────────────────┐        ┌─────────────┐
│      Frontend       │        │   Agent Backend      │        │     MCP Server      │        │  OMDb API   │
│   React + Vite      │──────▶ │  FastAPI + LangChain │──────▶ │     FastAPI         │──────▶ │ omdbapi.com │
│   localhost:3000    │        │   localhost:8000     │        │   localhost:8001    │        │             │
└─────────────────────┘        └──────────────────────┘        └─────────────────────┘        └─────────────┘
```

---

## Tech Stack

| Service         | Technology                              | Purpose                                              |
|-----------------|-----------------------------------------|------------------------------------------------------|
| Frontend        | React 18, Vite, CSS                     | Chat UI — sends messages, renders agent responses    |
| Agent Backend   | Python, FastAPI, LangChain, Groq LLM    | Runs the LLM agent; selects and calls MCP tools      |
| MCP Server      | Python, FastAPI, Requests               | Wraps OMDb API into structured HTTP endpoints        |
| LLM             | Groq — `llama-3.3-70b-versatile`        | Tool-calling language model powering the agent       |
| Movie Data      | OMDb API                                | Source of all movie and TV series information        |

---

## Prerequisites

**Option A — Docker (recommended)**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)

**Option B — Local setup**
- Python 3.9+
- Node 18+

---

## API Keys Required

Both keys are free to obtain:

| Key              | Where to get it                                                        |
|------------------|------------------------------------------------------------------------|
| `OMDB_API_KEY`   | [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)         |
| `GROQ_API_KEY`   | [console.groq.com](https://console.groq.com)                           |

---

## Quick Start with Docker

**1. Clone the repository**
```bash
git clone <repo-url>
cd movie-agent
```

**2. Create your `.env` file**
```bash
cp .env.example .env
# Open .env and fill in your OMDB_API_KEY and GROQ_API_KEY
```

**3. Build and start all services**
```bash
docker compose up --build
```

**4. Open the app**

Navigate to [http://localhost:3000](http://localhost:3000)

---

## Verify Services Are Healthy

Once running, check each service responds:

| Service         | Health URL                                      |
|-----------------|-------------------------------------------------|
| Frontend        | http://localhost:3000                           |
| Agent Backend   | http://localhost:8000/health                    |
| MCP Server      | http://localhost:8001/health                    |

The agent backend will not start until the MCP server passes its health check.

---

## Local Setup Without Docker

> **Start order matters:** MCP Server → Agent Backend → Frontend

### 1. MCP Server (port 8001)
```bash
cd mcp-server
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "OMDB_API_KEY=your_key_here" > .env
uvicorn main:app --port 8001 --reload
```

### 2. Agent Backend (port 8000)
```bash
cd agent-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
echo "MCP_SERVER_URL=http://localhost:8001" >> .env
uvicorn main:app --port 8000 --reload
```

### 3. Frontend (port 5173)
```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
movie-agent/
├── docker-compose.yml          # Orchestrates all three services
├── .env.example                # Template — copy to .env and fill in keys
│
├── mcp-server/
│   ├── main.py                 # FastAPI app with all OMDb endpoints
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile
│   └── .dockerignore
│
├── agent-backend/
│   ├── main.py                 # FastAPI app exposing /chat and /reset
│   ├── agent.py                # LangChain agent setup (Groq LLM + tools)
│   ├── tools.py                # LangChain tools wrapping MCP server endpoints
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile
│   └── .dockerignore
│
└── frontend/
    ├── src/
    │   ├── App.jsx             # Root component, chat state management
    │   ├── components/
    │   │   ├── ChatWindow.jsx  # Renders conversation history
    │   │   └── ChatInput.jsx   # Message input and submit
    │   └── index.css           # Global styles
    ├── nginx.conf              # Nginx SPA config with try_files fallback
    ├── vite.config.js          # Vite build configuration
    ├── Dockerfile
    └── .dockerignore
```

---

## MCP Server Endpoints

| Method | Path          | Description                                                    |
|--------|---------------|----------------------------------------------------------------|
| GET    | `/health`     | Liveness check — returns `{"status": "ok"}`                    |
| GET    | `/search`     | Search movies/shows by title keyword (`?query=`)               |
| GET    | `/details`    | Full movie details by title (`?title=`) — plot, cast, director |
| GET    | `/ratings`    | IMDb, Rotten Tomatoes, and Metacritic scores (`?title=`)       |
| GET    | `/series`     | TV series details including season count (`?title=`)           |
| GET    | `/year-search`| Keyword search filtered by release year (`?query=&year=`)      |

---

## Example Questions

Ask the agent anything like:

1. *"What is Inception about and who directed it?"*
2. *"How many seasons does Breaking Bad have?"*
3. *"What did critics think of Parasite? Show me the Rotten Tomatoes score."*
4. *"Find me some Batman movies from 2008."*
5. *"Recommend something similar to The Dark Knight."*
6. *"Who stars in Stranger Things and what's its IMDb rating?"*

---

## Deployment Notes

All three services are fully stateless — conversation history is owned by the browser and passed on each request, so the agent backend holds no session state between calls. This makes horizontal scaling straightforward: any number of agent-backend or mcp-server replicas can run behind a load balancer without sticky sessions or shared memory. The `/health` endpoints on both Python services are ready for use as liveness and readiness probes in Kubernetes or any container orchestration platform that supports health-check-gated traffic routing.
