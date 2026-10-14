from dataclasses import FrozenInstanceError
from typing import List

import pytest

from clean_dom import CleaningResult, CleaningStats, DOMCleaner


class CharacterTokenizer:
    """Simple deterministic tokenizer used to test the tokenizer interface."""

    def encode(self, text: str) -> List[str]:
        """Return one token per character."""
        return list(text)


def test_clean_with_report_keeps_clean_api_behavior_unchanged():
    html = '<script>remove</script><div onclick="x">Hello</div>'
    cleaner = DOMCleaner()

    result = cleaner.clean_with_report(html)

    assert isinstance(cleaner.clean(html), str)
    assert result.cleaned_html == cleaner.clean(html)
    assert isinstance(result, CleaningResult)
    assert isinstance(result.stats, CleaningStats)


def test_report_contains_character_counts_and_reduction():
    html = "<script>remove me</script><p>Hello</p>"
    result = DOMCleaner().clean_with_report(html)

    assert result.stats.input_chars == len(html)
    assert result.stats.output_chars == len(result.cleaned_html)
    assert result.stats.chars_saved == len(html) - len(result.cleaned_html)
    assert result.stats.char_reduction_percent == pytest.approx(
        result.stats.chars_saved / len(html) * 100
    )


def test_token_fields_are_none_when_tokenizer_is_disabled():
    stats = DOMCleaner().clean_with_report("<p>Text</p>").stats

    assert stats.input_tokens is None
    assert stats.output_tokens is None
    assert stats.tokens_saved is None
    assert stats.token_reduction_percent is None
    assert stats.max_tokens is None
    assert stats.budget_met is None
    assert stats.strategy_level is None


def test_custom_tokenizer_reports_token_counts():
    html = "<script>remove</script><p>Hi</p>"
    result = DOMCleaner().clean_with_report(html, tokenizer=CharacterTokenizer())

    assert result.stats.input_tokens == len(html)
    assert result.stats.output_tokens == len(result.cleaned_html)
    assert result.stats.tokens_saved == len(html) - len(result.cleaned_html)
    input_tokens = result.stats.input_tokens
    tokens_saved = result.stats.tokens_saved
    assert input_tokens is not None
    assert tokens_saved is not None
    assert result.stats.token_reduction_percent == pytest.approx(
        tokens_saved / input_tokens * 100
    )


def test_tiktoken_reports_counts_when_optional_dependency_is_installed():
    tiktoken = pytest.importorskip("tiktoken")
    html = "<script>remove</script><p>Hello world</p>"
    result = DOMCleaner().clean_with_report(html, tokenizer="tiktoken")
    encoding = tiktoken.get_encoding("cl100k_base")

    assert result.stats.input_tokens == len(encoding.encode(html))
    assert result.stats.output_tokens == len(encoding.encode(result.cleaned_html))


def test_missing_tiktoken_has_install_guidance(monkeypatch):
    import builtins

    from clean_dom import _tokenizers

    original_import = builtins.__import__

    def import_without_tiktoken(name, *args, **kwargs):
        if name == "tiktoken":
            raise ModuleNotFoundError("No module named 'tiktoken'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_tiktoken)
    _tokenizers._get_tiktoken_encoder.cache_clear()
    with pytest.raises(ImportError, match=r'pip install "clean-dom\[tokens\]"'):
        DOMCleaner().clean_with_report("<p>Text</p>", tokenizer="tiktoken")
    _tokenizers._get_tiktoken_encoder.cache_clear()


def test_empty_input_has_zero_counts_and_reduction():
    stats = DOMCleaner().clean_with_report("").stats

    assert stats.input_chars == 0
    assert stats.output_chars == 0
    assert stats.chars_saved == 0
    assert stats.char_reduction_percent == 0.0
    assert stats.input_tokens is None
    assert stats.token_reduction_percent is None


@pytest.mark.parametrize("html", ["<p>Καλημέρα κόσμε 👋</p>", "<div>你好，世界</div>"])
def test_unicode_character_counts_use_python_string_length(html):
    result = DOMCleaner().clean_with_report(html)

    assert result.stats.input_chars == len(html)
    assert result.stats.output_chars == len(result.cleaned_html)
    assert result.cleaned_html


def test_malformed_html_is_cleaned_and_reported():
    html = "<div><p>Unclosed <span>nested</p>"
    result = DOMCleaner().clean_with_report(html)

    assert "Unclosed" in result.cleaned_html
    assert "nested" in result.cleaned_html
    assert result.stats.output_chars == len(result.cleaned_html)


def test_cleaning_models_are_immutable():
    result = DOMCleaner().clean_with_report("<p>Text</p>")
    stats_field = "input_chars"
    result_field = "cleaned_html"

    with pytest.raises(FrozenInstanceError):
        setattr(result.stats, stats_field, 0)
    with pytest.raises(FrozenInstanceError):
        setattr(result, result_field, "")
