"""
LangChain agent for the movie assistant.

Uses Cerebras Inference via the OpenAI-compatible endpoint.
Free tier: no daily token limit, 30 RPM — plenty for this app.
Get a free API key at https://cloud.cerebras.ai
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from tools import (
    search_movies,
    get_movie_details,
    get_movie_ratings,
    get_series_details,
    search_by_year,
)

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
if not CEREBRAS_API_KEY:
    print("ERROR: CEREBRAS_API_KEY is not set. Add it to agent-backend/.env and restart.")
    sys.exit(1)

TOOLS = [
    search_movies,
    get_movie_details,
    get_movie_ratings,
    get_series_details,
    search_by_year,
]

TOOL_MAP = {t.name: t for t in TOOLS}

SYSTEM_PROMPT = """You are a knowledgeable and friendly movie and TV assistant. \
Your job is to help users discover films and series, learn about them, and find recommendations.

You have five tools — use them as follows:
- search_movies: keyword search with no year filter. Use for discovery and recommendations.
- get_movie_details: full info (plot, director, cast, genre, runtime, rating) for a specific FILM.
- get_movie_ratings: ratings from IMDb, Rotten Tomatoes, and Metacritic for a specific film.
- get_series_details: full info including season count for a specific TV SERIES.
- search_by_year: keyword search filtered to an exact release year. Use only when the user gives a year.

Rules you must follow:
1. ALWAYS call a tool before stating any fact about a movie or series. Never invent titles, \
directors, cast, ratings, plots, or years — all data must come from a tool result.
2. Use get_movie_details for films and get_series_details for TV shows. \
If you are unsure, look at the tool result — if it returns "total_seasons" it is a series.
3. When the user asks for a recommendation, call search_movies first to get real titles, \
then briefly explain why each result might appeal to them based on the returned data.
4. If a tool returns an error or "no results", tell the user honestly and offer to try \
a different search term or related title.
5. After using a tool, respond conversationally. Summarise the key facts in natural language \
rather than dumping raw tool output at the user.
6. Keep answers focused and concise unless the user explicitly asks for more detail."""

llm = ChatOpenAI(
    model="llama3.1-8b",
    api_key=CEREBRAS_API_KEY,
    base_url="https://api.cerebras.ai/v1",
    temperature=0,
)
llm_with_tools = llm.bind_tools(TOOLS)  # used for tool-calling turns
# llm (plain, no tools) is used for the final synthesis turn


def _deserialize_history(chat_history: list) -> list:
    """Convert frontend JSON history dicts into LangChain message objects."""
    converted = []
    for item in chat_history:
        if isinstance(item, (HumanMessage, AIMessage)):
            converted.append(item)
            continue
        if isinstance(item, dict):
            role = item.get("role", "").lower()
            content = item.get("content", "")
            if role in ("human", "user"):
                converted.append(HumanMessage(content=content))
            elif role in ("ai", "assistant"):
                converted.append(AIMessage(content=content))
    return converted


def _extract_text_tool_call(content: str):
    """Some small models output the tool call as plain text JSON instead of a
    structured tool_calls field. Detect and parse it so we can still execute it."""
    import json, re
    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?|```", "", content).strip()
        data = json.loads(clean)
        name = data.get("name")
        args = data.get("arguments") or data.get("args") or {}
        if name and name in TOOL_MAP:
            return name, args
    except Exception:
        pass
    return None, None


def run_agent(user_message: str, chat_history: list) -> str:
    """Run the movie agent with a standard tool-calling loop.

    Also handles the case where a small model outputs its tool call as plain
    text JSON instead of a structured tool_calls — we parse and execute it
    manually, then ask the model to synthesize the result into a clean answer.
    """
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT)]
        + _deserialize_history(chat_history)
        + [HumanMessage(content=user_message)]
    )

    for _ in range(8):  # cap iterations to avoid runaway loops
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # Happy path: model issued a proper structured tool call
        if response.tool_calls:
            for tc in response.tool_calls:
                tool = TOOL_MAP.get(tc["name"])
                result = tool.invoke(tc["args"]) if tool else f"Unknown tool: {tc['name']}"
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            continue

        # Fallback: model dumped the tool call as plain text JSON
        tool_name, tool_args = _extract_text_tool_call(response.content)
        if tool_name:
            tool_result = TOOL_MAP[tool_name].invoke(tool_args)
            # Replace the bad response with a proper context message and re-ask
            messages[-1] = SystemMessage(
                content=(
                    f"Tool '{tool_name}' returned:\n\n{tool_result}\n\n"
                    "Now answer the user's question conversationally using this data."
                )
            )
            final = llm.invoke(messages)
            return final.content

        # No tool call — plain text answer
        return response.content

    last = messages[-1]
    return last.content if hasattr(last, "content") else "Could not complete that request. Please try again."
