# SDFormat 1.12 Ontology Crawler & Builder

This project is a toolset designed to crawl the [SDFormat 1.12 Specification](https://sdformat.org/spec/1.12/) and build a semantic ontology (in Turtle format) representing the model hierarchy and its attributes.

## Features

- **Automated Crawling**: Extracts the hierarchical structure of SDFormat elements (e.g., `<model>`, `<link>`, `<joint>`, `<sensor>`) directly from the official specification pages.
- **Deep Structure Enrichment**: Automatically expands nested elements (like `<link>` and `<joint>`) by crawling their specific definition pages and merging them into the main model structure.
- **Ontology Generation**: Converts the extracted JSON structure into an OWL ontology (`.ttl` file), defining classes for complex elements and properties for attributes.
- **Interactive Visualization**: Provides a web-based tree view (`tree_view.html`) to explore the complex SDFormat hierarchy, with search and expand/collapse functionality.
- **Independent Element Extraction**: Can extract and save the structure of all SDFormat elements (e.g., `world`, `scene`, `physics`) into separate JSON files.

## Project Structure

- **`enrich_structure.py`**: The core script. It crawls the `model` page, then recursively visits and merges sub-element pages (like `link`, `joint`, `sensor`) to build a complete, deep hierarchy. Handles recursion depth and node duplication.
- **`build_ontology.py`**: Reads the merged JSON structure (`structure.json`) and generates the Turtle ontology file (`sdformat_model.ttl`).
- **`tree_view.html`**: An interactive HTML file to visualize the generated `structure.json` as a collapsible tree.
- **`extract_all.py`**: A utility script to crawl ALL available elements from the SDFormat index and save them as individual JSON files in the `structures/` directory.
- **`structures/`**: Directory containing independent JSON structure files for each element (e.g., `structure_world.json`, `structure_sensor.json`).
- **`sdformat_model.ttl`**: The generated ontology file.
- **`structure.json`**: The final, merged JSON representation of the SDFormat model hierarchy.

## Usage

1.  **Install Dependencies**:
    ```bash
    pip install requests
    ```

2.  **Crawl and Build Structure**:
    To crawl the model hierarchy and enrich it with sub-element definitions:
    ```bash
    python enrich_structure.py
    ```
    This will generate `structure.json` (the complete merged structure).

3.  **Generate Ontology**:
    To build the OWL ontology from the structure:
    ```bash
    python build_ontology.py
    ```
    This creates `sdformat_model.ttl`.

4.  **Visualize**:
    Open `tree_view.html` in your web browser to explore the hierarchy interactively.

5.  **Extract All Elements**:
    To download the structure of every SDFormat element independently:
    ```bash
    python extract_all.py
    ```
    Check the `structures/` folder for the output files.

## Technical Details

- **Parsing**: Uses Python's built-in `html.parser` for lightweight and dependency-free HTML parsing.
- **Recursion Handling**: Implements depth limits and context-aware expansion to prevent infinite loops (e.g., `joint` inside `mimic` inside `joint`).
- **Data Format**: Intermediate data is stored in JSON, preserving the nested nature of XML/SDF elements.

## License

This project is for educational and research purposes. SDFormat specifications are property of their respective owners.
