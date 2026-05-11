print("Step 1: starting...")

try:
    from dotenv import load_dotenv
    print("Step 2: dotenv imported OK")
except Exception as e:
    print(f"Step 2 FAILED: {e}")

try:
    import os
    load_dotenv()
    key = os.getenv("JSEARCH_API_KEY")
    print(f"Step 3: Key = '{key}'")
except Exception as e:
    print(f"Step 3 FAILED: {e}")

try:
    import requests
    print("Step 4: requests imported OK")
except Exception as e:
    print(f"Step 4 FAILED: {e}")
    exit()

try:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {"query": "Software Engineer in Malaysia", "page": "1", "num_pages": "1"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"Step 5: Status code = {resp.status_code}")
    print(f"Step 5: Response = {resp.text[:300]}")
except Exception as e:
    print(f"Step 5 FAILED: {e}")