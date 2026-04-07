
import requests
from html.parser import HTMLParser

url = "https://sdformat.org/spec/1.9/model"
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        if 'class="tree well"' in response.text:
            print("Found 'tree well' structure!")
        else:
            print("Did NOT find 'tree well' structure.")
            # Print a snippet to see what it looks like
            print(response.text[:500])
except Exception as e:
    print(f"Error: {e}")
