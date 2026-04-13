import time
import requests

BASE_URL = "http://localhost:8001"


def print_result(label, data):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    if isinstance(data, list):
        for item in data:
            print(item)
    else:
        for key, value in data.items():
            print(f"  {key}: {value}")


def test_search():
    response = requests.get(f"{BASE_URL}/search", params={"query": "Inception"})
    print_result("GET /search  |  query='Inception'", response.json())


def test_details():
    response = requests.get(f"{BASE_URL}/details", params={"title": "The Dark Knight"})
    print_result("GET /details  |  title='The Dark Knight'", response.json())


def test_ratings():
    response = requests.get(f"{BASE_URL}/ratings", params={"title": "Interstellar"})
    print_result("GET /ratings  |  title='Interstellar'", response.json())


def test_series():
    response = requests.get(f"{BASE_URL}/series", params={"title": "Breaking Bad"})
    print_result("GET /series  |  title='Breaking Bad'", response.json())


def test_year_search():
    response = requests.get(
        f"{BASE_URL}/year-search", params={"query": "Batman", "year": "2008"}
    )
    print_result("GET /year-search  |  query='Batman'  year='2008'", response.json())


if __name__ == "__main__":
    print("Running MCP server tests against", BASE_URL)

    test_search()
    time.sleep(0.5)

    test_details()
    time.sleep(0.5)

    test_ratings()
    time.sleep(0.5)

    test_series()
    time.sleep(0.5)

    test_year_search()

    print(f"\n{'=' * 60}")
    print("  All tests complete.")
    print(f"{'=' * 60}\n")
