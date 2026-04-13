"""
LangChain agent for the movie assistant.

Uses ChatOpenAI pointed at Groq's OpenAI-compatible endpoint with a manual
tool-calling loop. The manual loop lets us intercept Groq's 400/tool_use_failed
errors — which happen when llama-3.3-70b-versatile generates its native
<function=name{...}> syntax instead of JSON — parse the failed_generation field,
execute the tool ourselves, and continue the conversation normally.
"""

import os
import re
import sys
import json
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY is not set. Add it to agent-backend/.env and restart.")
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

# Use langchain-openai → Groq's OpenAI-compatible endpoint so tool calls are
# always sent as standard JSON schema. langchain-groq lets Llama fall back to
# its native <function=...> format, which Groq's API then rejects with a 400.
llm = ChatOpenAI(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0,
)
llm_with_tools = llm.bind_tools(TOOLS)

# Matches Llama's native function-call format inside Groq's error string:
# <function=tool_name{"arg": "value"}</function>
_FAILED_GEN_RE = re.compile(
    r"<function=(?P<name>\w+)(?P<args>\{.*?\})(?:</function>)?",
    re.DOTALL,
)


def _parse_failed_generation(error_str: str):
    """Extract tool name and parsed args from a Groq tool_use_failed error string."""
    m = _FAILED_GEN_RE.search(error_str)
    if not m:
        return None, None
    try:
        return m.group("name"), json.loads(m.group("args"))
    except json.JSONDecodeError:
        return None, None


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


def run_agent(user_message: str, chat_history: list) -> str:
    """Run the movie agent with a manual tool-calling loop and format-error recovery.

    On each iteration we call the LLM. Three outcomes:
      1. Model returns a normal text response → return it.
      2. Model returns a valid tool_call → execute the tool, append result, loop.
      3. Groq raises 400/tool_use_failed (model used native Llama format) →
         parse failed_generation, run the tool ourselves, ask the LLM to
         synthesize the result, return that.
    """
    messages = (
        [SystemMessage(content=SYSTEM_PROMPT)]
        + _deserialize_history(chat_history)
        + [HumanMessage(content=user_message)]
    )

    for _ in range(8):  # cap iterations to avoid runaway loops
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as exc:
            err = str(exc)
            if "tool_use_failed" not in err:
                raise

            # ── Recovery path ──────────────────────────────────────────────
            # Groq rejected the model's native <function=...> call. Parse it,
            # run the tool ourselves, then ask the LLM to answer from the result.
            tool_name, tool_args = _parse_failed_generation(err)
            if tool_name and tool_name in TOOL_MAP:
                tool_result = TOOL_MAP[tool_name].invoke(tool_args)
                messages.append(
                    SystemMessage(
                        content=(
                            f"The tool '{tool_name}' returned the following data:\n\n"
                            f"{tool_result}\n\n"
                            "Use this data to answer the user's question conversationally."
                        )
                    )
                )
                recovery = llm.invoke(messages)  # plain LLM, no tools
                return recovery.content

            # Could not recover — surface a clean error
            raise RuntimeError(
                f"Tool call failed and could not be recovered (tool='{tool_name}'). "
                "Please try rephrasing your question."
            ) from exc

        # Normal path
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tc in response.tool_calls:
            tool = TOOL_MAP.get(tc["name"])
            if tool:
                result = tool.invoke(tc["args"])
            else:
                result = f"Unknown tool requested: {tc['name']}"
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    # Fallback if max iterations hit
    last = messages[-1]
    return last.content if hasattr(last, "content") else "Could not complete that request. Please try again."
