import requests

url = "https://sdformat.org/spec/1.12/model/"
try:
    response = requests.get(url)
    response.raise_for_status()
    with open("page_content.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Successfully downloaded page content.")
except Exception as e:
    print(f"Error: {e}")
