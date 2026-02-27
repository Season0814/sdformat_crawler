import requests
from html.parser import HTMLParser

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

url = "https://sdformat.org/spec/1.12/"
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    parser = LinkParser()
    parser.feed(response.text)
    
    # Filter potential element links
    # They usually look like "world" or "scene" without extensions, or "world.html"
    # Let's see what we get
    print("Found links:")
    for link in parser.links[:50]: # Print first 50
        print(link)
        
except Exception as e:
    print(e)
