# clean-dom

`clean-dom` is a lightweight DOM compression and cleaning layer for LLM and
AI-agent pipelines. It removes configurable HTML noise while retaining useful
HTML structure and semantic attributes for browser agents, web scrapers, and
automation workflows.

Unlike traditional HTML-to-Markdown conversion, which flattens much of the DOM
structure, `clean-dom` prunes the existing HTML representation. This can make
page context more compact while preserving the markup your downstream workflow
needs.

The amount of output reduction depends on each page and its content.

## Installation

```bash
pip install clean-dom

Basic Usage
from clean_dom import DOMCleanerraw_html = """<html>  <head>    <style>body { background: red; }</style>    <script src="analytics.js"></script>  </head>  <body>    <div        id="main-container"        class="content"        data-tracker="xyz123"    >      <h1 class="title">Hello LLM!</h1>      <a href="https://example.com" onclick="trackClick()">        Read More      </a>    </div>  </body></html>"""cleaner = DOMCleaner()cleaned_html = cleaner.clean(raw_html)print(cleaned_html)


By default, the cleaner removes common non-content elements such as scripts,
styles, navigation, footers, embedded frames, SVGs, and canvas elements.
It also:
- removes HTML comments
- filters attributes using a semantic allowlist
- removes data: URLs from src and href
- removes excessively large attribute values
Removal Rules
You can add extra elements to the default removal rules:
from clean_dom import DOMCleanercleaner = DOMCleaner(    additional_remove_tags={"aside", "footer"})cleaned_html = cleaner.clean(raw_html)


There are three related options:
remove_tags
Replaces the default removal set completely.
cleaner = DOMCleaner(    remove_tags={"script", "aside"})


Only the tags you specify will be removed.
additional_remove_tags
Adds tags to the default removal set.
cleaner = DOMCleaner(    additional_remove_tags={"aside"})


This keeps all default cleaning rules and also removes aside.
unwrap_tags
Removes the wrapper element while preserving its text and child elements.
cleaner = DOMCleaner(    unwrap_tags={"span"})


For example:
<p>Hello <span>world</span></p>

becomes approximately:
<p>Hello world</p>

The text world is preserved.
Attributes
By default, clean-dom preserves useful semantic and interaction attributes,
including:
- id
- class
- href
- src
- alt
- title
- name
- type
- value
- placeholder
- role
- aria-label
- aria-labelledby
- for
- action
- method
- checked
- selected
- disabled
- required
You can provide your own whitelist:
cleaner = DOMCleaner(    allowed_attributes={"id", "href", "aria-label"})


AI Agent Preset
For browser agents and automation workflows:
cleaner = DOMCleaner.preset("agent")cleaned_html = cleaner.clean(raw_html)


The agent preset keeps useful form and accessibility information such as:
- role
- aria-label
- name
- type
- placeholder
This helps downstream AI systems understand interactive page elements such as
buttons, links, and form fields.
Presets
clean-dom includes three built-in presets.
minimal
cleaner = DOMCleaner.preset("minimal")


Keeps only the id and href attributes while using the default tag-removal
rules.
content
cleaner = DOMCleaner.preset("content")


Uses the default removal rules, additionally removes aside, and unwraps
span elements.
agent
cleaner = DOMCleaner.preset("agent")


Preserves additional semantic, accessibility, and form attributes useful for
AI agents and browser automation.
Additional Configuration
HTML comments are removed by default.
To preserve them:
cleaner = DOMCleaner(    remove_comments=False)


data: URLs are removed from src and href by default.
To preserve them:
cleaner = DOMCleaner(    drop_data_urls=False)


Attribute values longer than 500 characters are removed by default.
You can change the limit:
cleaner = DOMCleaner(    max_attribute_length=1000)


Or disable the limit:
cleaner = DOMCleaner(    max_attribute_length=None)


Backwards Compatibility
The old strip_tags argument from clean-dom 0.1.x is temporarily supported
for backwards compatibility.
cleaner = DOMCleaner(    strip_tags={"script", "style"})


However, strip_tags is deprecated.
New code should use:
cleaner = DOMCleaner(    remove_tags={"script", "style"})


Why clean-dom?
Large HTML snapshots often contain significant amounts of information that is
not useful to an LLM or browser agent, including:
- JavaScript
- CSS
- tracking attributes
- SVG markup
- iframes
- navigation boilerplate
- large embedded data URLs
- unnecessary HTML attributes
Sending all of this to an LLM can increase context size and introduce noise.
clean-dom provides a deterministic preprocessing step:
Raw HTML
   ↓
clean-dom
   ↓
Smaller, cleaner DOM
   ↓
LLM / AI agent

It preserves HTML structure rather than converting the page into Markdown,
making it useful when downstream systems need to reason about DOM elements,
links, forms, IDs, or accessibility information.
Safety
clean-dom is a DOM pruning and context-optimization library.
It is not an HTML security sanitizer.
Do not use it as a replacement for dedicated security sanitization tools when
rendering untrusted HTML in a browser or application.
Development
Clone the repository and install development dependencies:
git clone https://github.com/AfroditiTzama/clean-dom.git
cd clean-dom
pip install -e ".[dev]"

Run the test suite:
python -m pytest -v

Run Ruff:
python -m ruff check src tests examples

Run Pyright:
pyright

Build the package:
python -m build

Validate the distributions:
python -m twine check dist/*

Contributing
Contributions, bug reports, and feature requests are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance.
License
Distributed under the MIT License.
See LICENSE for more information.