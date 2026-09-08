# 🎬 Movie Agent

An AI-powered movie assistant that answers natural-language questions about films and TV shows using real-time data from the OMDb API.

**🔗 Live demo:** [movie-frontend-ghxj.onrender.com](https://movie-frontend-ghxj.onrender.com/)

> Deployed on Render's free tier — the backend and MCP server spin down after ~15 minutes of inactivity, so the first message after a quiet period can take 30–50s to wake them up. Subsequent messages are fast.

---

## Architecture

Three independently deployable services, each with a single job:

```
┌──────────────────┐        ┌────────────────────┐        ┌──────────────────┐        ┌─────────────┐
│     Frontend      │        │   Agent Backend     │        │    MCP Server     │        │  OMDb API   │
│  React + Vite      │──────▶│  FastAPI + LangChain │──────▶│     FastAPI        │──────▶│ omdbapi.com  │
│  (chat UI)         │◀──────│  (the "brain")       │◀──────│  (data adapter)    │◀──────│              │
└──────────────────┘        └────────────────────┘        └──────────────────┘        └─────────────┘
```

| Service       | Local URL             | Deployed URL                                                     |
|---------------|------------------------|--------------------------------------------------------------------|
| Frontend      | http://localhost:5173 (Docker: `:3000`) | https://movie-frontend-ghxj.onrender.com |
| Agent Backend | http://localhost:8000  | Render web service (Docker) — see `MCP_SERVER_URL`/`VITE_AGENT_URL` wiring in `render.yaml` |
| MCP Server    | http://localhost:8001  | Render web service (Docker) |

### Why three services instead of one?

- **Frontend** never talks to OMDb or the LLM directly — it only knows one thing: the agent backend's `/chat` endpoint. This keeps API keys off the browser entirely.
- **MCP Server** is a thin, dumb translation layer: it wraps OMDb's REST API into a small set of clean, typed endpoints (`/search`, `/details`, `/ratings`, `/series`, `/year-search`). It has no LLM logic in it at all — it could be reused by any agent, not just this one.
- **Agent Backend** is the only service that holds an LLM. It decides *which* MCP endpoint to call based on the user's question, and turns raw JSON results into a natural-language answer.

This separation is what MCP (Model Context Protocol) is about: keep "the model that decides" separate from "the tools that fetch data," so either side can change independently.

## Data Flow: what happens when you send a message

1. **Browser → Frontend**: You type a question in the chat UI. `App.jsx` POSTs it to the agent backend's `/chat` endpoint, along with the running conversation history (the frontend is the only place chat history lives — the backend is fully stateless).
2. **Frontend → Agent Backend**: `main.py`'s `/chat` route hands the message to `run_agent()` in `agent.py`.
3. **Agent Backend → LLM (Groq)**: The agent sends the system prompt + conversation to Groq's `openai/gpt-oss-120b` model, with the five movie tools (`search_movies`, `get_movie_details`, `get_movie_ratings`, `get_series_details`, `search_by_year`) bound to the call. The model decides whether it needs a tool, and if so, which one and with what arguments.
4. **Agent Backend → MCP Server**: If the model requested a tool call, `tools.py` makes an HTTP request to the corresponding MCP server endpoint (e.g. `GET /details?title=...`).
5. **MCP Server → OMDb API**: The MCP server translates that into an OMDb API call, using the `OMDB_API_KEY`, and normalizes the response into clean JSON.
6. **Result flows back up**: MCP Server → Agent Backend → the tool result is fed back to the LLM, which synthesizes a natural-language reply (this loop can repeat, since the agent can call multiple tools per question, up to 8 iterations as a safety cap).
7. **Agent Backend → Frontend**: The final reply is returned as `{"response": "..."}`. The frontend appends it to the visible chat and to the history it will send on the next turn.

Nothing is stored server-side at any point — kill and restart the agent backend mid-conversation and nothing is lost, because the browser owns the entire conversation state.

---

## Tech Stack

| Service         | Technology                                  | Purpose                                              |
|-----------------|---------------------------------------------|------------------------------------------------------|
| Frontend        | React 18, Vite, CSS                         | Chat UI — sends messages, renders agent responses    |
| Agent Backend   | Python, FastAPI, LangChain, Groq LLM        | Runs the LLM agent; selects and calls MCP tools      |
| MCP Server      | Python, FastAPI, Requests                   | Wraps OMDb API into structured HTTP endpoints        |
| LLM             | Groq API — `openai/gpt-oss-120b`            | Tool-calling language model powering the agent       |
| Movie Data      | OMDb API                                    | Source of all movie and TV series information        |
| Hosting         | Render (Blueprint — see `render.yaml`)      | All three services deployed as connected Render web services / static site |

---

## Prerequisites

**Option A — Docker (recommended)**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)

**Option B — Local setup**
- Python 3.9+
- Node 18+

---

## API Keys Required

Both keys are free to obtain, no credit card needed:

| Key              | Where to get it                                                                       |
|------------------|-----------------------------------------------------------------------------------------|
| `OMDB_API_KEY`   | [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)                          |
| `GROQ_API_KEY`   | [console.groq.com/keys](https://console.groq.com/keys) (sign in to create an API key)   |

---

## Quick Start with Docker

**1. Clone the repository**
```bash
git clone <repo-url>
cd movie-agent
```

**2. Create your `.env` file** (at the repo root — `docker-compose.yml` reads from here)
```bash
cp .env.example .env
# Open .env and fill in your OMDB_API_KEY and GROQ_API_KEY
```

**3. Build and start all services**
```bash
docker compose up --build
```
This starts the services in dependency order automatically: `mcp-server` first, then `agent-backend` (which waits for the MCP server's healthcheck to pass), then `frontend`. Add `-d` to run detached, and `docker compose logs -f` to tail all three logs together.

**4. Open the app**

Navigate to [http://localhost:3000](http://localhost:3000)

**5. Stopping / resetting**
```bash
docker compose down          # stop and remove containers
docker compose up --build    # rebuild after a code change (Compose caches layers, so this is usually fast)
```

---

## Verify Services Are Healthy

Once running, check each service responds:

| Service         | Health URL                                      |
|-----------------|-------------------------------------------------|
| Frontend        | http://localhost:3000                           |
| Agent Backend   | http://localhost:8000/health                    |
| MCP Server      | http://localhost:8001/health                    |

The agent backend will not start until the MCP server passes its health check. If `docker compose up` seems to hang, run `docker compose ps` in another terminal — a service stuck in a restart loop usually means a missing/invalid API key in `.env`.

---

## Local Setup Without Docker

> **Start order matters:** MCP Server → Agent Backend → Frontend — each one checks the previous one is reachable.
> Use three separate terminal tabs, one per service, and leave each `uvicorn`/`npm run dev` process running.

### 1. MCP Server (port 8001)
```bash
cd mcp-server
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "OMDB_API_KEY=your_key_here" > .env
uvicorn main:app --port 8001 --reload
```
Confirm it's up: `curl http://localhost:8001/health`

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
Confirm it's up: `curl http://localhost:8000/health` — this will fail fast with a clear error if the MCP server isn't reachable yet.

### 3. Frontend (port 5173)
```bash
cd frontend
npm install
npm run dev
```
The frontend talks to `http://localhost:8000` by default in dev (see `VITE_AGENT_URL` in [frontend/.env.example](frontend/.env.example) if you ever need to point it elsewhere, e.g. at a deployed backend).

Open [http://localhost:5173](http://localhost:5173).

---

## Deploying Your Own Copy

This repo ships a [`render.yaml`](render.yaml) Blueprint that deploys all three services together on [Render](https://render.com):

1. Push the repo to your own GitHub account.
2. On Render: **New → Blueprint**, select the repo — it reads `render.yaml` and proposes `movie-mcp-server`, `movie-agent-backend`, and `movie-frontend` (a static site).
3. When prompted, fill in `OMDB_API_KEY` and `GROQ_API_KEY` (kept out of the repo via `sync: false`).
4. Apply. Once all three show "Live", open the frontend's URL.

Since Render assigns URLs from the service `name` (and `.onrender.com` subdomains are globally unique), if your names collide with someone else's, Render will suffix them — update `MCP_SERVER_URL` (on `movie-agent-backend`) and `VITE_AGENT_URL` (on `movie-frontend`) in the dashboard to match, then trigger a manual redeploy of the frontend (Vite bakes env vars in at build time, so a plain env var change alone won't take effect until it rebuilds).

---

## Project Structure

```
movie-agent/
├── render.yaml                 # Render Blueprint — defines all 3 deployed services
├── docker-compose.yml          # Orchestrates all three services locally
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
│   ├── agent.py                # LangChain agent setup (Groq LLM (openai/gpt-oss-120b) + tools)
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
    ├── .env.example             # VITE_AGENT_URL template for pointing at a different backend
    ├── nginx.conf               # Nginx SPA config with try_files fallback (used by frontend/Dockerfile for local Docker only — Render deploys it as a static site instead)
    ├── vite.config.js           # Vite build configuration
    ├── Dockerfile
    └── .dockerignore
```

---

## MCP Server Endpoints

| Method | Path          | Description                                                    |
|--------|---------------|------------------------------------------------------------------|
| GET    | `/health`     | Liveness check — returns `{"status": "ok"}`                    |
| GET    | `/search`     | Search movies/shows by title keyword (`?query=`)               |
| GET    | `/details`    | Full movie details by title (`?title=`) — plot, cast, director |
| GET    | `/ratings`    | IMDb, Rotten Tomatoes, and Metacritic scores (`?title=`)       |
| GET    | `/series`     | TV series details including season count (`?title=`)           |
| GET    | `/year-search`| Keyword search filtered by release year (`?query=&year=`)      |

## Agent Backend Endpoints

| Method | Path      | Description                                                          |
|--------|-----------|------------------------------------------------------------------------|
| GET    | `/health` | Liveness check — returns `{"status": "ok", "model": "..."}`          |
| POST   | `/chat`   | `{"message": "...", "chat_history": [...]}` → `{"response": "..."}`  |
| POST   | `/reset`  | Client-side confirmation that history was cleared (no server state to actually reset) |

---

## Example Questions

Ask the agent anything like:

1. *"What is Presitge about and who directed it?"*
2. *"How many seasons does Breaking Bad have?"*
3. *"What did critics think of Parasite? Show me the Rotten Tomatoes score."*
4. *"Find me some Batman movies from 2008."*
5. *"Recommend something similar to The Dark Knight."*
6. *"Who stars in Stranger Things and what's its IMDb rating?"*

---

## Deployment Notes

All three services are fully stateless — conversation history is owned by the browser and passed on each request, so the agent backend holds no session state between calls. This makes horizontal scaling straightforward: any number of agent-backend or mcp-server replicas can run behind a load balancer without sticky sessions or shared memory. The `/health` endpoints on both Python services are ready for use as liveness and readiness probes in Kubernetes or any container orchestration platform that supports health-check-gated traffic routing.
