import requests

def check_url(url):
    try:
        response = requests.get(url)
        print(f"{url}: {response.status_code}")
    except Exception as e:
        print(f"{url}: Error {e}")

check_url("https://sdformat.org/spec/1.12/link")
check_url("https://sdformat.org/spec/1.12/joint")
