import json
import requests
from html.parser import HTMLParser
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich_structure import extract_structure_from_url

def get_all_element_names(base_url):
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
            print(f"Failed to fetch index: {response.status_code}")
            return []
        
        links = set()
        class LinkParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    href = dict(attrs).get("href")
                    # Filter for simple element names 
                    # They should be just words like "world", "model"
                    # Exclude "index.html", "style.css", relative paths, etc.
                    if href and not href.startswith(".") and not href.startswith("http") and "#" not in href and "/" not in href:
                         if not href.endswith(".html") and not href.endswith(".css") and not href.endswith(".js"):
                            links.add(href)
        
        parser = LinkParser()
        parser.feed(response.text)
        return list(links)
    except Exception as e:
        print(f"Error fetching index: {e}")
        return []

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract SDFormat structures for a specific version.")
    parser.add_argument("version", nargs="?", default="1.12", help="SDFormat version (e.g., 1.9, 1.12)")
    args = parser.parse_args()
    
    version = args.version
    base_url = f"https://sdformat.org/spec/{version}/"
    output_dir = PROJECT_ROOT / "data" / "structures" / version
    
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {output_dir}")
        
    print(f"Fetching element list from {base_url}...")
    elements = get_all_element_names(base_url)
    
    # Manually add likely missing ones if any, or known ones that might be missed
    # But checking the output of check_index.py, it seems to cover most.
    # We saw: sdf, world, scene, state, physics, light, actor, model, link, sensor, joint, collision, visual, material, geometry
    
    # Sort for consistent order
    elements.sort()
    
    print(f"Found {len(elements)} elements: {elements}")
    
    for name in elements:
        # Skip if name is empty or weird
        if not name: continue
        
        url = base_url + name
        print(f"Extracting {name}...")
        try:
            struct = extract_structure_from_url(url, name)
            if struct:
                filename = output_dir / f"structure_{name}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(struct, f, indent=2, ensure_ascii=False)
                print(f"Saved {filename}")
            else:
                print(f"No structure found for {name}")
        except Exception as e:
            print(f"Failed to process {name}: {e}")

if __name__ == "__main__":
    main()
