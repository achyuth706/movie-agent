"""
LangChain tools for the movie agent.

Each tool wraps one MCP server endpoint. The Gemini agent inspects each
tool's name and docstring to decide which tool to call and with what input.
MCP_SERVER_URL is loaded from .env so the base URL can be changed without
touching code.
"""

import os
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

_UNREACHABLE = (
    "The movie data service is currently unreachable. "
    "Please try again in a moment."
)


@tool
def search_movies(query: str) -> str:
    """Search for movies or TV shows by a title keyword — use when no specific year is given.

    Use this tool when the user wants to browse or discover titles that contain
    a keyword, e.g. "find movies about space", "any film with 'dark' in the
    title", or "search for Batman movies" (without a specific year). Also use
    this as the first step for open-ended recommendations — search first, then
    describe the results.

    Do NOT use this tool if the user mentions a specific year; use
    search_by_year instead.
    Do NOT use this tool if the user asks for full details about one specific
    title they already know; use get_movie_details or get_series_details instead.

    Args:
        query: A keyword or partial title to search for (e.g. "inception",
               "batman", "lord of the rings").

    Returns:
        A formatted string listing matching titles with year, type, and IMDb
        ID, or an error message if nothing was found or the service failed.
    """
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/search", params={"query": query}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (RequestsConnectionError, Timeout):
        return _UNREACHABLE
    except Exception as exc:
        return f"Unexpected error searching for '{query}': {exc}"

    if isinstance(data, dict) and "error" in data:
        return f"No results found for '{query}': {data['error']}"

    lines = [f"Search results for '{query}':"]
    for movie in data:
        lines.append(
            f"  - {movie.get('title')} ({movie.get('year')}) "
            f"[{movie.get('type')}] — IMDb ID: {movie.get('imdb_id')}"
        )
    return "\n".join(lines)


@tool
def get_movie_details(title: str) -> str:
    """Get full details for a specific FILM (not a TV series) by its title.

    Use this tool when the user asks for information about a particular movie
    they have already named — its plot, director, cast, genre, runtime, or
    IMDb rating. This is the right tool for questions like "What is Inception
    about?", "Who directed The Dark Knight?", "How long is Parasite?", or
    "What genre is Joker?".

    Do NOT use this tool for TV series; use get_series_details instead.
    Do NOT use this tool if the user's primary question is about ratings/scores;
    use get_movie_ratings for that.

    Args:
        title: The exact or approximate film title (e.g. "The Dark Knight",
               "Inception", "Parasite", "The Godfather").

    Returns:
        A formatted string with title, year, genre, director, actors, runtime,
        IMDb rating, and full plot, or an error message if not found.
    """
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/details", params={"title": title}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (RequestsConnectionError, Timeout):
        return _UNREACHABLE
    except Exception as exc:
        return f"Unexpected error fetching details for '{title}': {exc}"

    if "error" in data:
        return f"Could not find details for '{title}': {data['error']}"

    return (
        f"Title:       {data.get('title')}\n"
        f"Year:        {data.get('year')}\n"
        f"Genre:       {data.get('genre')}\n"
        f"Director:    {data.get('director')}\n"
        f"Actors:      {data.get('actors')}\n"
        f"Runtime:     {data.get('runtime')}\n"
        f"IMDb Rating: {data.get('imdb_rating')}\n"
        f"Plot:        {data.get('plot')}"
    )


@tool
def get_movie_ratings(title: str) -> str:
    """Get critic and audience ratings for a specific movie from all rating sources.

    Use this tool specifically when the user's question is about ratings,
    scores, or critical reception — e.g. "What did critics think of
    Interstellar?", "What's the Rotten Tomatoes score for X?", "Is Y well
    rated?", or "How does Z score on Metacritic?". Returns scores from IMDb,
    Rotten Tomatoes, and Metacritic where available.

    Do NOT use this tool for general movie info (plot, cast, director) — use
    get_movie_details for that.

    Args:
        title: The film title to fetch ratings for (e.g. "Interstellar",
               "The Godfather", "Everything Everywhere All at Once").

    Returns:
        A formatted string with the title, year, and all available rating
        scores, or an error message if the title was not found.
    """
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/ratings", params={"title": title}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (RequestsConnectionError, Timeout):
        return _UNREACHABLE
    except Exception as exc:
        return f"Unexpected error fetching ratings for '{title}': {exc}"

    if "error" in data:
        return f"Could not find ratings for '{title}': {data['error']}"

    lines = [f"Ratings for {data.get('title')} ({data.get('year')}):"]
    for rating in data.get("ratings", []):
        lines.append(f"  - {rating.get('Source')}: {rating.get('Value')}")
    if len(lines) == 1:
        lines.append("  No ratings available.")
    return "\n".join(lines)


@tool
def get_series_details(title: str) -> str:
    """Get details for a TV series (not a film) by its title.

    Use this tool when the user asks about a television show — e.g. "Tell me
    about Breaking Bad", "How many seasons does Game of Thrones have?", "Who
    stars in Stranger Things?", or "What is The Wire about?". This tool
    returns series-specific data including total season count.

    Do NOT use this tool for films; use get_movie_details for those.
    If you are unsure whether something is a film or a series, prefer this
    tool for titles widely known as TV shows.

    Args:
        title: The TV series title (e.g. "Breaking Bad", "Game of Thrones",
               "The Wire", "Stranger Things").

    Returns:
        A formatted string with title, year, total seasons, genre, actors,
        IMDb rating, and plot, or an error message if the series was not found.
    """
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/series", params={"title": title}, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (RequestsConnectionError, Timeout):
        return _UNREACHABLE
    except Exception as exc:
        return f"Unexpected error fetching series '{title}': {exc}"

    if "error" in data:
        return f"Could not find series '{title}': {data['error']}"

    return (
        f"Title:         {data.get('title')}\n"
        f"Year:          {data.get('year')}\n"
        f"Total Seasons: {data.get('total_seasons')}\n"
        f"Genre:         {data.get('genre')}\n"
        f"Actors:        {data.get('actors')}\n"
        f"IMDb Rating:   {data.get('imdb_rating')}\n"
        f"Plot:          {data.get('plot')}"
    )


@tool
def search_by_year(query_and_year: str) -> str:
    """Search for movies or shows by keyword AND a specific release year.

    Use this tool ONLY when the user specifies both a title keyword AND a
    year — e.g. "Batman movies from 2008", "the 2019 Joker", "Spider-Man
    2021". This narrows results to a single year, which is essential when a
    franchise has multiple entries across different years.

    Do NOT use this tool if no year is mentioned; use search_movies instead.

    Args:
        query_and_year: Keyword and year joined by a pipe in the format
                        "keyword|year" (e.g. "Batman|2008", "Joker|2019",
                        "Spider-Man|2021").

    Returns:
        A formatted string listing matching titles for that year with IMDb
        IDs, or an error message if nothing was found or the format was wrong.
    """
    if "|" not in query_and_year:
        return (
            "Invalid input format. Expected 'title|year' "
            f"(e.g. 'Batman|2008'), got: '{query_and_year}'"
        )

    query, year = query_and_year.split("|", 1)
    query, year = query.strip(), year.strip()

    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/year-search",
            params={"query": query, "year": year},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (RequestsConnectionError, Timeout):
        return _UNREACHABLE
    except Exception as exc:
        return f"Unexpected error searching for '{query}' ({year}): {exc}"

    if isinstance(data, dict) and "error" in data:
        return f"No results for '{query}' in {year}: {data['error']}"

    lines = [f"Search results for '{query}' ({year}):"]
    for movie in data:
        lines.append(
            f"  - {movie.get('title')} ({movie.get('year')}) "
            f"[{movie.get('type')}] — IMDb ID: {movie.get('imdb_id')}"
        )
    return "\n".join(lines)
