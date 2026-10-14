# clean-dom

`clean-dom` is a lightweight DOM compression and cleaning layer for LLM and AI-agent pipelines.

It removes configurable HTML noise while preserving useful DOM structure, semantic attributes, links, form controls, and accessibility information.

Unlike HTML-to-Markdown converters, `clean-dom` keeps the DOM structure intact so downstream systems can still reason about elements, forms, links, IDs, and browser-agent interactions.

> Output reduction depends on the page, cleaner configuration, and tokenizer.

---

## Installation

Basic installation:

```bash
pip install clean-dom
```

For token counting:

```bash
pip install "clean-dom[tokens]"
```

---

## Quick Start

```python
from clean_dom import DOMCleaner

raw_html = """
<html>
  <head>
    <style>body { background: red; }</style>
    <script src="analytics.js"></script>
  </head>

  <body>
    <div
        id="main-container"
        class="content"
        data-tracker="xyz123"
    >
      <h1>Hello LLM!</h1>

      <a
          href="https://example.com"
          onclick="trackClick()"
      >
        Read More
      </a>
    </div>
  </body>
</html>
"""

cleaner = DOMCleaner()

cleaned_html = cleaner.clean(raw_html)

print(cleaned_html)
```

By default, `clean-dom` removes common DOM noise such as:

- scripts
- styles
- SVGs
- iframes
- canvas elements
- navigation and footer containers
- HTML comments
- unwanted attributes
- `data:` URLs
- excessively large attribute values

Useful semantic attributes are preserved.

---

## Token Metrics

Use `clean_with_report()` to inspect character and token reduction.

```python
from clean_dom import DOMCleaner

cleaner = DOMCleaner()

result = cleaner.clean_with_report(
    html,
    tokenizer="tiktoken",
)

print(result.stats.input_tokens)
print(result.stats.output_tokens)
print(result.stats.tokens_saved)
print(result.stats.token_reduction_percent)
```

Token counting requires:

```bash
pip install "clean-dom[tokens]"
```

The current optional tokenizer integration uses `tiktoken` with the `cl100k_base` encoding.

Character statistics are available without token dependencies.

---

## Token Budget Mode

`clean-dom` can progressively reduce DOM noise to try to fit a target token budget.

```python
result = cleaner.clean_to_budget(
    html,
    max_tokens=8000,
    tokenizer="tiktoken",
)

print(result.stats.output_tokens)
print(result.stats.budget_met)
print(result.stats.strategy_level)
```

Budget mode applies increasingly aggressive cleaning strategies rather than blindly cutting raw HTML in the middle of markup.

A requested token budget is **not guaranteed** to be achievable if the remaining content is itself too large.

---

## Element Mapping for AI Agents

Browser agents often need a stable way to refer to actionable DOM elements.

Use:

```python
result = cleaner.clean_with_mapping(html)

print(result.cleaned_html)
print(result.element_map[1])
```

The resulting HTML may look like:

```html
<a href="/pricing" data-cdom-id="1">
  Pricing
</a>

<button data-cdom-id="2">
  Start free trial
</button>
```

`clean-dom` assigns deterministic integer IDs to useful elements such as:

- links
- buttons
- inputs
- selects
- textareas
- forms
- labels
- elements with roles
- elements with accessibility labels

Native HTML `id` attributes are preserved.

For example:

```html
<button id="buy-now" data-cdom-id="7">
  Buy now
</button>
```

The mapping uses integer keys based on final cleaned DOM traversal order.

---

## Repeated Section Deduplication

Repeated subtree deduplication is available as an opt-in feature.

```python
cleaner = DOMCleaner(
    deduplicate_repeated_sections=True
)

cleaned_html = cleaner.clean(html)
```

The matcher is intentionally conservative.

It only compares sibling subtrees under the same parent and considers:

- tag structure
- normalized text
- cleaned attributes
- links
- form actions
- semantic differences

For example, these are **not** treated as duplicates:

```html
<a href="/product/1">Buy</a>
<a href="/product/2">Buy</a>
```

because their destinations differ.

Report-based APIs expose:

```python
result.stats.duplicate_sections_removed
result.stats.duplicate_chars_removed
```

---

## Presets

`clean-dom` includes three built-in presets.

### Minimal

```python
cleaner = DOMCleaner.preset("minimal")
```

Keeps only a small attribute set such as `id` and `href`.

Useful when DOM size matters more than rich interaction metadata.

---

### Content

```python
cleaner = DOMCleaner.preset("content")
```

Optimized for readable page content.

It removes additional low-priority containers and unwraps unnecessary wrapper elements such as `span`.

---

### Agent

```python
cleaner = DOMCleaner.preset("agent")
```

Designed for browser agents and automation workflows.

It preserves useful attributes such as:

- `role`
- `aria-label`
- `aria-labelledby`
- `name`
- `type`
- `value`
- `placeholder`
- `action`
- `method`
- `checked`
- `selected`
- `disabled`
- `required`

Unlike the default cleaner, the `agent` preset preserves `nav` and `footer` containers so agents can still access:

- category links
- breadcrumbs
- pagination
- navigation menus
- footer actions

---

## Custom Removal Rules

### Replace the default removal set

```python
cleaner = DOMCleaner(
    remove_tags={"script", "aside"}
)
```

`remove_tags` completely replaces the default tag-removal configuration.

---

### Extend the default removal set

```python
cleaner = DOMCleaner(
    additional_remove_tags={"aside"}
)
```

This keeps the default rules and adds more tags to remove.

---

### Unwrap tags without deleting their contents

```python
cleaner = DOMCleaner(
    unwrap_tags={"span"}
)
```

Input:

```html
<p>Hello <span>world</span></p>
```

Output:

```html
<p>Hello world</p>
```

The wrapper disappears, but its text and child elements remain.

---

## Attribute Filtering

By default, `clean-dom` preserves useful semantic and interactive attributes including:

- `id`
- `class`
- `href`
- `src`
- `alt`
- `title`
- `name`
- `type`
- `value`
- `placeholder`
- `role`
- `aria-label`
- `aria-labelledby`
- `for`
- `action`
- `method`
- `checked`
- `selected`
- `disabled`
- `required`

You can provide your own allowlist:

```python
cleaner = DOMCleaner(
    allowed_attributes={
        "id",
        "href",
        "aria-label",
    }
)
```

---

## Additional Configuration

### Preserve HTML comments

Comments are removed by default.

```python
cleaner = DOMCleaner(
    remove_comments=False
)
```

---

### Preserve `data:` URLs

`data:` URLs in `src` and `href` are removed by default.

```python
cleaner = DOMCleaner(
    drop_data_urls=False
)
```

---

### Attribute length limits

Attribute values longer than 500 characters are removed by default.

Change the limit:

```python
cleaner = DOMCleaner(
    max_attribute_length=1000
)
```

Disable the limit:

```python
cleaner = DOMCleaner(
    max_attribute_length=None
)
```

---

## Benchmarks

`clean-dom` includes a committed synthetic-realistic benchmark suite covering:

- documentation pages
- long-form articles
- e-commerce listings
- React-style application shells
- news pages
- navigation-heavy pages

The suite measures:

- character reduction
- token reduction
- semantic retention
- median runtime
- p95 runtime
- deduplication behavior

Run:

```bash
uv sync --extra dev --extra tokens

uv run --extra dev --extra tokens \
  python benchmarks/run_benchmarks.py
```

Example from the committed e-commerce fixture:

- token reduction: **25.0%**
- required semantic retention: **100%**

These results are specific to the committed fixture, tokenizer, configuration, and machine. They are **not universal expected savings**.

See [BENCHMARKS.md](BENCHMARKS.md) for methodology and limitations.

---

## Why clean-dom?

Raw browser HTML often contains large amounts of information that does not help an LLM reason about a page:

- JavaScript
- CSS
- tracking attributes
- embedded SVG markup
- hidden metadata
- oversized attributes
- repeated boilerplate
- unnecessary wrappers

A typical pipeline becomes:

```text
Raw HTML
   ↓
clean-dom
   ↓
Smaller structured DOM
   ↓
LLM / AI agent
```

The key difference from Markdown conversion is that `clean-dom` keeps the DOM representation.

That makes it useful when downstream systems still need to reason about:

- links
- buttons
- forms
- DOM hierarchy
- native IDs
- accessibility metadata
- actionable elements

---

## Backwards Compatibility

The old `strip_tags` argument from `clean-dom 0.1.x` remains temporarily supported.

```python
cleaner = DOMCleaner(
    strip_tags={"script", "style"}
)
```

It is deprecated.

New code should use:

```python
cleaner = DOMCleaner(
    remove_tags={"script", "style"}
)
```

---

## Safety

`clean-dom` is a DOM pruning and context-optimization library.

It is **not an HTML security sanitizer**.

Do not use it as a replacement for dedicated sanitization tools when rendering untrusted HTML in a browser or application.

---

## Development

Clone the repository:

```bash
git clone https://github.com/AfroditiTzama/clean-dom.git
cd clean-dom
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -v
```

Run Ruff:

```bash
python -m ruff check src tests examples benchmarks
```

Run Pyright:

```bash
pyright
```

Build distributions:

```bash
python -m build
```

Validate distributions:

```bash
python -m twine check dist/*
```

---

## Contributing

Contributions, bug reports, and feature requests are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Distributed under the MIT License.

See [LICENSE](LICENSE).
