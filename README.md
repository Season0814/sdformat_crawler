# SDFormat Ontology Crawler & Builder (1.12 / 1.9)

This project is a toolset designed to crawl the SDFormat specification (e.g. [1.12](https://sdformat.org/spec/1.12/), [1.9](https://sdformat.org/spec/1.9/)) and build a semantic ontology representing the model hierarchy and its attributes.

## Features

- **Automated Crawling**: Extracts the hierarchical structure of SDFormat elements (e.g., `<model>`, `<link>`, `<joint>`, `<sensor>`) directly from the official specification pages.
- **Deep Structure Enrichment**: Automatically expands nested elements (like `<link>` and `<joint>`) by crawling their specific definition pages and merging them into the main model structure.
- **Ontology Generation**: Converts the extracted JSON structure into OWL ontologies:
  - Turtle: `sdformat_model.ttl`
  - RDF/XML: `sdformat_model.owl`
  - Edges-only RDF/XML (no `subClassOf` / `Restriction`): `sdformat_model_edges.owl`
- **Interactive Visualization**: Provides a web-based tree view (`tree_view.html`) to explore the complex SDFormat hierarchy, with search and expand/collapse functionality.
- **Independent Element Extraction**: Can extract and save the structure of all SDFormat elements (e.g., `world`, `scene`, `physics`) into separate JSON files, separated by spec version.

## Project Structure

- **`enrich_structure.py`**: The core script. It crawls the `model` page, then recursively visits and merges sub-element pages (like `link`, `joint`, `sensor`) to build a complete, deep hierarchy. Handles recursion depth and node duplication.
- **`build_ontology.py`**: Reads the merged JSON structure (`structure.json`) and generates the ontology files (`sdformat_model.ttl`, `sdformat_model.owl`, `sdformat_model_edges.owl`).
- **`tree_view.html`**: An interactive HTML file to visualize the generated `structure.json` as a collapsible tree.
- **`extract_all.py`**: A utility script to crawl ALL available elements from a given SDFormat version and save them as individual JSON files in the `structures/<version>/` directory.
- **`structures/`**: Directory containing independent JSON structure files for each element, separated by version (e.g., `structures/1.12/structure_world.json`, `structures/1.9/structure_sensor.json`).
- **`sdformat_model.ttl`**: The generated ontology file (Turtle).
- **`sdformat_model.owl`**: The generated ontology file (RDF/XML).
- **`sdformat_model_edges.owl`**: The generated edges-only ontology file (RDF/XML).
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
    This creates `sdformat_model.ttl`, `sdformat_model.owl`, and `sdformat_model_edges.owl`.

4.  **Visualize**:
    Open `tree_view.html` in your web browser to explore the hierarchy interactively.

5.  **Extract All Elements**:
    To download the structure of every SDFormat element independently:
    ```bash
    python extract_all.py 1.12
    python extract_all.py 1.9
    ```
    Check the `structures/<version>/` folder for the output files.

## Technical Details

- **Parsing**: Uses Python's built-in `html.parser` for lightweight and dependency-free HTML parsing.
- **Recursion Handling**: Implements depth limits and context-aware expansion to prevent infinite loops (e.g., `joint` inside `mimic` inside `joint`).
- **Data Format**: Intermediate data is stored in JSON, preserving the nested nature of XML/SDF elements.

## License

This project is for educational and research purposes. SDFormat specifications are property of their respective owners.
