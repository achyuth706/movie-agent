"""
MCP Movie Server
================
A FastAPI microservice that wraps the OMDb API (http://www.omdbapi.com/) and
exposes movie data as HTTP endpoints consumed by the LangChain agent-backend.

Endpoints
---------
GET /health        — Liveness check. Returns {"status": "ok"}.
GET /search        — Search movies by title keyword (OMDb s= param).
GET /details       — Full movie details by title (OMDb t= param, plot=full).
GET /ratings       — Ratings from all sources (IMDb, Rotten Tomatoes, Metacritic).
GET /series        — TV series details by title (OMDb type=series).
GET /year-search   — Title keyword search filtered by release year (OMDb y= param).
GET /cache/stats   — Number of cached items and total cache hits.
DELETE /cache      — Clear the entire in-memory cache.

Error conventions
-----------------
400 — Required query parameter is missing or blank.
404 — OMDb returned Response=False (title not found, no search results, etc.).
500 — Unexpected error communicating with OMDb or processing the response.
"""

import os
import sys
import time
import requests
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if not OMDB_API_KEY:
    print("ERROR: OMDB_API_KEY is not set. Add it to mcp-server/.env and restart.")
    sys.exit(1)

OMDB_BASE_URL = "http://www.omdbapi.com/"
CACHE_TTL = 3600  # seconds (1 hour)

# ---------------------------------------------------------------------------
# In-memory cache
# Each entry: {"data": <response payload>, "ts": <unix timestamp>}
# ---------------------------------------------------------------------------
_cache: dict[str, dict] = {}
_hits: int = 0


def _cache_get(key: str):
    """Return cached value for key if present and not expired, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() - entry["ts"] > CACHE_TTL:
        del _cache[key]
        return None
    return entry["data"]


def _cache_set(key: str, data) -> None:
    """Store data in cache with current timestamp."""
    _cache[key] = {"data": data, "ts": time.time()}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="MCP Movie Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Return 400 instead of FastAPI's default 422 for missing/invalid query params."""
    missing = [e["loc"][-1] for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": f"Missing or invalid parameter(s): {', '.join(str(m) for m in missing)}"},
    )


# ---------------------------------------------------------------------------
# Health / cache management
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cache/stats")
def cache_stats():
    """Return the number of currently cached items and total cache hits."""
    # Evict expired entries before counting
    expired = [k for k, v in _cache.items() if time.time() - v["ts"] > CACHE_TTL]
    for k in expired:
        del _cache[k]
    return {"cached_items": len(_cache), "cache_hits": _hits}


@app.delete("/cache")
def clear_cache():
    """Clear all entries from the in-memory cache."""
    global _hits
    count = len(_cache)
    _cache.clear()
    _hits = 0
    return {"cleared": count, "message": "Cache cleared."}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/search")
def search(query: str):
    """Search OMDb for movies matching a title keyword.

    Args:
        query: Title keyword to search for.

    Returns:
        A list of matching movies, each with title, year, imdb_id, and type.

    Raises:
        HTTPException 404: If OMDb returns no results for the query.
        HTTPException 500: If the OMDb request fails unexpectedly.
    """
    global _hits
    key = f"search:{query.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        _hits += 1
        print(f"[CACHE HIT]  search '{query}'")
        return cached

    print(f"[CACHE MISS] search '{query}' — calling OMDb")
    try:
        response = requests.get(OMDB_BASE_URL, params={"apikey": OMDB_API_KEY, "s": query})
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OMDb request failed: {exc}")

    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "No results found."))

    result = [
        {
            "title": movie.get("Title"),
            "year": movie.get("Year"),
            "imdb_id": movie.get("imdbID"),
            "type": movie.get("Type"),
        }
        for movie in data.get("Search", [])
    ]
    _cache_set(key, result)
    return result


@app.get("/details")
def details(title: str):
    """Fetch full details for a movie by title.

    Args:
        title: The exact or approximate movie title to look up.

    Returns:
        A dict with title, year, genre, director, actors, plot, imdb_rating,
        and runtime.

    Raises:
        HTTPException 404: If OMDb cannot find the title.
        HTTPException 500: If the OMDb request fails unexpectedly.
    """
    global _hits
    key = f"details:{title.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        _hits += 1
        print(f"[CACHE HIT]  details '{title}'")
        return cached

    print(f"[CACHE MISS] details '{title}' — calling OMDb")
    try:
        response = requests.get(
            OMDB_BASE_URL,
            params={"apikey": OMDB_API_KEY, "t": title, "plot": "full"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OMDb request failed: {exc}")

    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "Movie not found."))

    result = {
        "title": data.get("Title"),
        "year": data.get("Year"),
        "genre": data.get("Genre"),
        "director": data.get("Director"),
        "actors": data.get("Actors"),
        "plot": data.get("Plot"),
        "imdb_rating": data.get("imdbRating"),
        "runtime": data.get("Runtime"),
    }
    _cache_set(key, result)
    return result


@app.get("/ratings")
def ratings(title: str):
    """Fetch ratings for a movie from all available sources.

    Args:
        title: The movie title to look up.

    Returns:
        A dict with title, year, and a ratings list containing each source
        (IMDb, Rotten Tomatoes, Metacritic) and its value.

    Raises:
        HTTPException 404: If OMDb cannot find the title.
        HTTPException 500: If the OMDb request fails unexpectedly.
    """
    global _hits
    key = f"ratings:{title.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        _hits += 1
        print(f"[CACHE HIT]  ratings '{title}'")
        return cached

    print(f"[CACHE MISS] ratings '{title}' — calling OMDb")
    try:
        response = requests.get(OMDB_BASE_URL, params={"apikey": OMDB_API_KEY, "t": title})
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OMDb request failed: {exc}")

    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "Movie not found."))

    result = {
        "title": data.get("Title"),
        "year": data.get("Year"),
        "ratings": data.get("Ratings", []),
    }
    _cache_set(key, result)
    return result


@app.get("/series")
def series(title: str):
    """Fetch details for a TV series by title.

    Args:
        title: The TV series title to look up.

    Returns:
        A dict with title, year, total_seasons, genre, actors, plot, and
        imdb_rating.

    Raises:
        HTTPException 404: If OMDb cannot find the series.
        HTTPException 500: If the OMDb request fails unexpectedly.
    """
    global _hits
    key = f"series:{title.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        _hits += 1
        print(f"[CACHE HIT]  series '{title}'")
        return cached

    print(f"[CACHE MISS] series '{title}' — calling OMDb")
    try:
        response = requests.get(
            OMDB_BASE_URL,
            params={"apikey": OMDB_API_KEY, "t": title, "type": "series", "plot": "full"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OMDb request failed: {exc}")

    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "Series not found."))

    result = {
        "title": data.get("Title"),
        "year": data.get("Year"),
        "total_seasons": data.get("totalSeasons"),
        "genre": data.get("Genre"),
        "actors": data.get("Actors"),
        "plot": data.get("Plot"),
        "imdb_rating": data.get("imdbRating"),
    }
    _cache_set(key, result)
    return result


@app.get("/year-search")
def year_search(query: str, year: str):
    """Search OMDb for movies matching a title keyword filtered by release year.

    Args:
        query: Title keyword to search for.
        year: Four-digit release year to filter results.

    Returns:
        A list of matching movies, each with title, year, imdb_id, and type.

    Raises:
        HTTPException 404: If OMDb returns no results for the query/year combination.
        HTTPException 500: If the OMDb request fails unexpectedly.
    """
    global _hits
    key = f"year-search:{query.lower()}:{year}"
    cached = _cache_get(key)
    if cached is not None:
        _hits += 1
        print(f"[CACHE HIT]  year-search '{query}' ({year})")
        return cached

    print(f"[CACHE MISS] year-search '{query}' ({year}) — calling OMDb")
    try:
        response = requests.get(
            OMDB_BASE_URL,
            params={"apikey": OMDB_API_KEY, "s": query, "y": year},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OMDb request failed: {exc}")

    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "No results found."))

    result = [
        {
            "title": movie.get("Title"),
            "year": movie.get("Year"),
            "imdb_id": movie.get("imdbID"),
            "type": movie.get("Type"),
        }
        for movie in data.get("Search", [])
    ]
    _cache_set(key, result)
    return result
