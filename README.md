# Clean DOM

[![CI](https://github.com/AfroditiTzama/clean-dom/actions/workflows/ci.yml/badge.svg)](https://github.com/AfroditiTzama/clean-dom/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

A lightweight Python library designed to prune and clean HTML DOM trees. It is specifically optimized to **reduce token usage and eliminate boilerplate** in Large Language Model (LLM) context windows, web scraping pipelines, and AI agents.

---

##  Why Clean DOM?

When feeding HTML snapshots from web scrapers or browser automation tools (like Playwright, Selenium) into LLMs, you often encounter massive amounts of useless bloat:
* **Tracking & Analytics:** Third-party scripts (`<script>`) and tracking pixels.
* **Styling Fluff:** Heavy embedded or inline CSS (`<style>`, `style="..."`).
* **Non-Semantic Assets:** SVGs, iframes, navbars, footers, and canvas elements.
* **Redundant Attributes:** Event handlers (`onclick`) and custom data trackers that inflate token counts without adding semantic meaning.

`clean-dom` strips this clutter efficiently, **slashing token consumption and API costs** while preserving the core structural content that LLMs actually need to reason about a webpage.

---

##  Installation

Install the package directly from source or via pip:

``bash
pip install .

For development (including testing frameworks and linters):

Bash
pip install -e ".[dev]"

## Quick Start
Out of the box, clean-dom requires zero configuration. It automatically targets and removes common noisy elements while keeping essential semantic attributes (id, class, href, src, etc.).

Python
from clean_dom import DOMCleaner

raw_html = """
<html>
  <head>
    <style>body { background: red; }</style>
    <script src="analytics.js"></script>
  </head>
  <body>
    <div id="main-container" class="content" data-tracker="xyz123">
      <h1 class="title">Hello LLM!</h1>
      <a href="[https://example.com](https://example.com)" onclick="trackClick()">Read More</a>
    </div>
  </body>
</html>
"""

## Initialize cleaner with default rules
cleaner = DOMCleaner()
cleaned_html = cleaner.clean(raw_html)

print(cleaned_html)
Output:

HTML
<html>
<head>
</head>
<body>
<div class="content" id="main-container">
<h1 class="title">Hello LLM!</h1>
<a href="[https://example.com](https://example.com)">Read More</a>
</div>
</body>
</html>

## Advanced Customization
If your AI agent or application requires custom pruning rules, you can easily pass your own configuration sets:

Python
from clean_dom import DOMCleaner

## Keep only specific tags/attributes or strip custom ones
cleaner = DOMCleaner(
    strip_tags={"span", "aside", "footer"},      # Additional tags to completely remove
    allowed_attributes={"id", "class", "href"}    # Strict whitelist of attributes to preserve
)

cleaned_html = cleaner.clean(raw_html)

## Performance & Benchmarks
Running the included benchmark script (python3 examples/benchmark.py) on typical bloated web snapshots demonstrates:

Token Reduction: Typically slashes HTML size by 45% to 70%, directly translating to lower API latency and cost savings with LLMs.

Execution Speed: Processes large HTML trees in sub-milliseconds (< 1ms), making it ideal for high-throughput asynchronous web scrapers.

## Running Tests
We maintain a rigorous test suite covering edge cases, malformed HTML, and custom configurations. To run tests and generate a code coverage report:

### Bash
python3 -m pytest --cov=clean_dom --cov-report=term-missing

### Contributing
Contributions, bug reports, and feature requests are warmly welcomed! Please read our CONTRIBUTING.md guide to get started.

### License
Distributed under the MIT License. See LICENSE for more information.
