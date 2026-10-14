# Changelog

## 0.2.1

### Added
- Optional token metrics and structured cleaning reports.
- Progressive token-budget cleaning and stable agent element mapping.
- Opt-in conservative repeated-sibling deduplication.
- Synthetic-realistic benchmark fixtures, runner, and semantic-retention checks.

### Changed
- The `agent` preset preserves navigation and footer containers for actionable links.

## 0.2.0

### Added
- `remove_tags` as the preferred replacement for `strip_tags`.
- `additional_remove_tags` and `unwrap_tags`.
- HTML comment removal, configurable maximum attribute length filtering, and
  filtering of `data:` URLs.
- `minimal`, `content`, and `agent` presets.
- Expanded semantic, form, and accessibility attributes useful for AI agents.

### Changed
- Improved DOM cleaning behavior for LLM and AI-agent pipelines.
- Improved package metadata and documentation.
- Improved CI with Ruff, Pyright, package building, and Twine validation.

### Deprecated
- `strip_tags` remains supported for backwards compatibility but is deprecated
  in favor of `remove_tags`.

### Fixed
- Empty `set()` configuration now behaves correctly.
- Improved malformed HTML and edge-case handling.
- Safer handling of oversized attributes and embedded data URLs.

## [0.1.0] - 2026-03-30
### Added
- Initial release of `clean-dom`.
- Core `DOMCleaner` class for stripping unwanted tags and filtering attributes.
- Comprehensive test suite with pytest.
- CI/CD workflow configuration via GitHub Actions.
