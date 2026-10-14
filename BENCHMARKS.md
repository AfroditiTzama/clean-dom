# Benchmark fixtures and runner

The committed fixtures are synthetic-realistic HTML patterns written for this
project. They are not copied full webpages and use neutral placeholder content.
They model common documentation, article, commerce, application, news, and
navigation structures, but do not represent every site or framework.

The set intentionally balances useful text and interactive structure with
ordinary removable markup. It avoids large scripts, styles, and data URLs.
The commerce fixture contains distinct products and destinations; the
navigation fixture contains one exact sibling menu copy alongside similar but
different links. `tests/test_benchmark_fixtures.py` checks these properties and
guards against accidental loss of distinct products during deduplication.

## Quality and retention

Each fixture declares exact `must_preserve_text`, `must_preserve_hrefs`, and
`must_preserve_attributes` expectations. `variant_expectations` adds required
items for modes whose purpose includes retaining more of the page shell, such
as the agent preset. Optional text and href expectations are reported as
diagnostics but do not fail a run. The manifest's `notes` explain these
differences.

Text matching collapses whitespace and then checks case-sensitive exact
phrases. Hrefs and attribute values use exact equality after HTML parsing. The
retention percentage is the number of preserved required text, href, and
attribute entries divided by the total number of required entries. Missing
required content makes both the regression tests and benchmark runner fail.
These explicit checks are not a complete measure of meaning.

The default cleaner removes `nav` and `footer`; tests confirm that this drops
navigation, breadcrumb, pagination, and footer links from the affected
fixtures. Those removals are useful for content-focused cleaning but can lose
agent-actionable links. The default behavior remains unchanged. The `agent`
preset now preserves `nav` and `footer` containers, and its fixture
expectations require those links to survive.

Compression, semantic retention, and runtime are considered together. High
token reduction is not automatically better if required useful information is
lost. Any statement about reduction should be tied to a specific fixture and
variant, for example: “On the committed ecommerce fixture, default cleaning
reduced tokens by the measured amount while preserving all explicitly
required benchmark semantics.” It should not be generalized to other pages.

## Run

Install the optional token counter and development tools, then run from the
repository root:

```bash
uv sync --extra dev --extra tokens
uv run --extra dev --extra tokens python benchmarks/run_benchmarks.py
```

The runner compares the default cleaner, the `agent` preset, and opt-in
repeated-section deduplication. It reports raw and cleaned character/token
counts, reduction percentages, required semantic retention, optional semantic
counts, and median and nearest-rank p95 runtime. Runtime includes parsing,
cleaning, and token counting; one warmup call is excluded.
Seven timed iterations are used by default. Use `--iterations 20` for a larger
sample, or repeat `--fixture docs.html` to select specific fixtures.

All inputs are committed local files. Normal execution does not access the
network. Token reduction depends on page structure and encoding. Results are
relative to these fixtures, the selected iteration count, and the local
machine; a percentage from this suite is not a universal expected gain.

## Review before sharing results

Run fixture integrity tests and the smoke benchmark before interpreting a
full run:

```bash
uv run --extra dev pytest tests/test_benchmark_fixtures.py
uv run --extra dev --extra tokens python benchmarks/run_benchmarks.py \
  --iterations 1 --fixture ecommerce.html
```

The fixture suite and its checks reduce obvious bias but cannot reproduce the
full diversity of live sites, browser-rendered content, or production latency.
Review output for each variant before sharing it.
