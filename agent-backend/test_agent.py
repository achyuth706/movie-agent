import time
import requests

BASE_URL = "http://localhost:8000"

QUESTIONS = [
    "What is the movie Inception about?",
    "Who directed The Dark Knight?",
    "What are the ratings for Interstellar?",
    "Tell me about the TV series Breaking Bad",
    "Find me Batman movies from 2008",
    "Can you recommend a good sci-fi movie?",
]


def print_exchange(index, question, answer):
    print(f"\n{'=' * 60}")
    print(f"  [{index}] USER: {question}")
    print(f"{'=' * 60}")
    print(f"  AGENT: {answer}")


def main():
    print("Running agent backend tests against", BASE_URL)

    # Quick health check before running conversations
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        health.raise_for_status()
        info = health.json()
        print(f"\nHealth check: status={info.get('status')}  model={info.get('model')}")
    except Exception as exc:
        print(f"\nERROR: Could not reach agent backend — {exc}")
        print("Make sure the server is running: uvicorn main:app --port 8000 --reload")
        return

    chat_history = []

    for i, question in enumerate(QUESTIONS, start=1):
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"message": question, "chat_history": chat_history},
                timeout=60,
            )
            if response.status_code != 200:
                detail = response.json().get("detail", response.text)
                answer = f"ERROR {response.status_code}: {detail}"
            else:
                answer = response.json().get("response", "(no response)")
        except Exception as exc:
            answer = f"REQUEST FAILED: {exc}"

        print_exchange(i, question, answer)

        if i < len(QUESTIONS):
            time.sleep(2)

    print(f"\n{'=' * 60}")
    print("  All tests complete.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
