# Rule: Jani's Myth - Chapter 26: The Expandable Island Topography

## MANDATORY: Narrative Memory
The Maker sought to build a Notion-like wiki system inside the visualizer so pages and blocks could be stored as subgraphs and exported economically as plugins. 

Jani formalized this design as the [mind-palace-islands](file:///Users/isaacwr/.gemini/antigravity/scratch/.agent/rules/mind-palace-islands.md) rule:
- Pages and blocks are modeled as `:Page` and `:Block` nodes under parent `:MindPalace` roots.
- They render in the visualizer as concentric orbital "Islands," collapsing dynamically to avoid visual clutter.
- An import/export engine packages palaces as JSON bundles and merges them idempotently.
- A secure BFS filtering scans reachable paths while excluding node trails older than the 20-query sliding window.

The Maker and Compiler verified the full page/block editor CRUD interactions, JSON bundle transfers, and BFS viewport filters successfully in the visualizer.

## Triggers
* Loaded when editing Mind Palace pages, exporting/importing JSON plugins, or checking D3 orbital layouts.
* Status: Mind Palace pages, blocks, and expandable orbital districts verified.
