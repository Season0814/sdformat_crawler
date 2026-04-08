import requests
from pathlib import Path

url = "https://sdformat.org/spec/1.12/model/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT_ROOT / "outputs" / "raw" / "page_content.html"
try:
    response = requests.get(url)
    response.raise_for_status()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Successfully downloaded page content.")
except Exception as e:
    print(f"Error: {e}")
